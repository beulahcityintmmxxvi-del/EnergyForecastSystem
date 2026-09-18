# forecasting/services/__init__.py
"""
Energy Forecasting Service
Adapted to the existing ForecastRun / ForecastResult models and
EnergyConsumption fields (reading_date, consumption_kwh).
"""
from datetime import timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.io import to_html
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from energy.models import Building, EnergyConsumption
from forecasting.models import ForecastResult, ForecastRun


class EnergyForecastingService:
    MIN_REQUIRED_DAYS = 14

    # ------------------------------------------------------------------ #
    #  DATA LOADING
    # ------------------------------------------------------------------ #
    @classmethod
    def load_building_dataframe(cls, building: Building) -> pd.DataFrame:
        """Return a clean daily DataFrame of consumption for *building*."""
        records = (
            EnergyConsumption.objects.filter(building=building)
            .order_by("reading_date")
            .values("reading_date", "consumption_kwh")
        )
        if not records.exists():
            return pd.DataFrame()

        df = pd.DataFrame(list(records))
        df.rename(
            columns={"reading_date": "date", "consumption_kwh": "kwh"},
            inplace=True,
        )
        df["date"] = pd.to_datetime(df["date"])
        df["kwh"] = df["kwh"].astype(float)

        # Aggregate multiple meter readings on the same day
        df = df.groupby("date", as_index=False)["kwh"].sum()
        df = df.set_index("date").asfreq("D")
        df["kwh"] = df["kwh"].interpolate(method="time").bfill().ffill()
        df = df.reset_index()
        return df

    # ------------------------------------------------------------------ #
    #  FEATURE ENGINEERING
    # ------------------------------------------------------------------ #
    @classmethod
    def generate_features(cls, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["dayofweek"] = df["date"].dt.dayofweek
        df["month"] = df["date"].dt.month
        df["day"] = df["date"].dt.day
        df["is_weekend"] = (df["dayofweek"] >= 5).astype(int)

        df["lag_1"] = df["kwh"].shift(1)
        df["lag_7"] = df["kwh"].shift(7)
        df["lag_14"] = df["kwh"].shift(14)
        df["rolling_7"] = df["kwh"].shift(1).rolling(7, min_periods=1).mean()
        df["rolling_14"] = df["kwh"].shift(1).rolling(14, min_periods=1).mean()
        return df

    # ------------------------------------------------------------------ #
    #  MAIN ENTRY POINT
    # ------------------------------------------------------------------ #
    @classmethod
    def run_forecast(
        cls,
        building: Building,
        periods: int = 30,
        user_label: str = "",
    ) -> ForecastRun:
        df = cls.load_building_dataframe(building)

        if len(df) < cls.MIN_REQUIRED_DAYS:
            raise ValueError(
                f"'{building.name}' needs at least {cls.MIN_REQUIRED_DAYS} days "
                f"of readings. Only {len(df)} available."
            )

        run = ForecastRun.objects.create(
            building=building,
            periods=periods,
            created_by=user_label,
        )

        try:
            # --- Validation split (last 20 %, max 30 days) ---
            val_size = min(max(7, int(len(df) * 0.2)), 30)
            train_df = df.iloc[:-val_size].copy()
            val_df = df.iloc[-val_size:].copy()

            metrics = cls._evaluate(train_df, val_df)
            run.mae = metrics["mae"]
            run.rmse = metrics["rmse"]
            run.mape = metrics["mape"]
            run.accuracy = max(0.0, 100.0 - metrics["mape"])

            # --- Predict future horizon ---
            preds_df = cls._predict_future(df, periods)

            results = [
                ForecastResult(
                    forecast_run=run,
                    forecast_date=row["date"].date(),
                    predicted_consumption=Decimal(f"{max(0, row['pred']):.2f}"),
                    lower_bound=Decimal(f"{max(0, row['lower']):.2f}"),
                    upper_bound=Decimal(f"{max(0, row['upper']):.2f}"),
                )
                for _, row in preds_df.iterrows()
            ]
            ForecastResult.objects.bulk_create(results)
            run.save()
            return run

        except Exception as exc:
            run.delete()
            raise exc

    # ------------------------------------------------------------------ #
    #  EVALUATION
    # ------------------------------------------------------------------ #
    @classmethod
    def _evaluate(cls, train_df, val_df) -> dict:
        full = pd.concat([train_df, val_df], ignore_index=True)
        feat = cls.generate_features(full).dropna()

        train_f = feat[feat["date"] < val_df["date"].min()]
        val_f = feat[feat["date"] >= val_df["date"].min()]

        cols = [
            "dayofweek", "month", "day", "is_weekend",
            "lag_1", "lag_7", "lag_14", "rolling_7", "rolling_14",
        ]
        X_tr, y_tr = train_f[cols], train_f["kwh"]
        X_va, y_va = val_f[cols], val_f["kwh"]

        model = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
        model.fit(X_tr, y_tr)
        y_pred = model.predict(X_va)

        mae = float(mean_absolute_error(y_va, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_va, y_pred)))
        nz = y_va != 0
        mape = float(np.mean(np.abs((y_va[nz] - y_pred[nz]) / y_va[nz])) * 100) if nz.any() else 0.0

        return {"mae": mae, "rmse": rmse, "mape": mape}

    # ------------------------------------------------------------------ #
    #  FUTURE PREDICTION (autoregressive roll-forward)
    # ------------------------------------------------------------------ #
    @classmethod
    def _predict_future(cls, df, horizon) -> pd.DataFrame:
        working = df.copy()
        cols = [
            "dayofweek", "month", "day", "is_weekend",
            "lag_1", "lag_7", "lag_14", "rolling_7", "rolling_14",
        ]

        feat = cls.generate_features(working).dropna()
        model = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
        model.fit(feat[cols], feat["kwh"])

        residuals = feat["kwh"] - model.predict(feat[cols])
        std_err = float(np.std(residuals)) if len(residuals) else float(feat["kwh"].mean() * 0.1)

        last_date = working["date"].max()
        out = []

        for step in range(1, horizon + 1):
            nxt = last_date + timedelta(days=step)
            tmp = pd.concat(
                [working, pd.DataFrame([{"date": nxt, "kwh": np.nan}])],
                ignore_index=True,
            )
            row_feat = cls.generate_features(tmp).iloc[[-1]]
            pred = max(0.0, float(model.predict(row_feat[cols])[0]))
            unc = 1.96 * std_err * np.sqrt(1 + step / horizon)

            out.append({
                "date": nxt,
                "pred": pred,
                "lower": max(0.0, pred - unc),
                "upper": pred + unc,
            })
            working = pd.concat(
                [working, pd.DataFrame([{"date": nxt, "kwh": pred}])],
                ignore_index=True,
            )

        return pd.DataFrame(out)

    # ------------------------------------------------------------------ #
    #  PLOTLY CHART
    # ------------------------------------------------------------------ #
    @classmethod
    def build_plot_html(cls, run: ForecastRun) -> str:
        hist = cls.load_building_dataframe(run.building).tail(60)
        vals = run.results.all().order_by("forecast_date")

        dates = [v.forecast_date for v in vals]
        preds = [float(v.predicted_consumption) for v in vals]
        lo = [float(v.lower_bound) if v.lower_bound else float(v.predicted_consumption) for v in vals]
        hi = [float(v.upper_bound) if v.upper_bound else float(v.predicted_consumption) for v in vals]

        fig = go.Figure()

        # Confidence band
        fig.add_trace(go.Scatter(
            x=dates, y=hi, mode="lines", line=dict(width=0),
            showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=dates, y=lo, mode="lines", line=dict(width=0),
            fill="tonexty", fillcolor="rgba(22,163,74,0.15)",
            name="95 % Confidence", hoverinfo="skip",
        ))

        # Historical actuals
        if not hist.empty:
            fig.add_trace(go.Scatter(
                x=hist["date"], y=hist["kwh"],
                mode="lines+markers", name="Actual (Historical)",
                line=dict(color="#0f766e", width=2.5), marker=dict(size=4),
            ))

        # Forecast line
        fig.add_trace(go.Scatter(
            x=dates, y=preds, mode="lines+markers",
            name="Forecasted kWh",
            line=dict(color="#16a34a", width=3, dash="dash"),
            marker=dict(size=5, symbol="diamond"),
        ))

        fig.update_layout(
            title=f"<b>{run.building.name}</b> — Energy Demand Forecast",
            xaxis_title="Date", yaxis_title="kWh",
            hovermode="x unified", template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=30, t=80, b=40),
            font=dict(family="Inter, sans-serif", size=12),
        )
        return to_html(fig, full_html=False, include_plotlyjs="cdn", config={"responsive": True})
