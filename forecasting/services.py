# forecasting/services.py
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
from .models import ForecastModelRun, ForecastValue


class EnergyForecastingService:
    MIN_REQUIRED_DAYS = 14

    @classmethod
    def load_building_dataframe(cls, building: Building) -> pd.DataFrame:
        """Fetch consumption records for a building ordered by date as a clean daily DataFrame."""
        records = (
            EnergyConsumption.objects.filter(building=building)
            .order_by("date")
            .values("date", "kwh_usage")
        )
        if not records.exists():
            return pd.DataFrame()

        df = pd.DataFrame(list(records))
        df["date"] = pd.to_datetime(df["date"])
        df["kwh_usage"] = df["kwh_usage"].astype(float)

        # Aggregate multiple meters/entries on the same date into daily sum
        df = df.groupby("date", as_index=False)["kwh_usage"].sum()
        df = df.set_index("date").asfreq("D")
        # Impute missing days via linear interpolation
        df["kwh_usage"] = df["kwh_usage"].interpolate(method="time").bfill().ffill()
        df = df.reset_index()
        return df

    @classmethod
    def generate_features(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer time-series and calendar features for ML models."""
        df = df.copy()
        df["dayofweek"] = df["date"].dt.dayofweek
        df["month"] = df["date"].dt.month
        df["day"] = df["date"].dt.day
        df["is_weekend"] = df["dayofweek"].apply(lambda x: 1 if x >= 5 else 0)

        # Lag features
        df["lag_1"] = df["kwh_usage"].shift(1)
        df["lag_7"] = df["kwh_usage"].shift(7)
        df["lag_14"] = df["kwh_usage"].shift(14)
        df["rolling_mean_7"] = df["kwh_usage"].shift(1).rolling(window=7, min_periods=1).mean()
        df["rolling_mean_14"] = df["kwh_usage"].shift(1).rolling(window=14, min_periods=1).mean()

        return df

    @classmethod
    def run_forecast(
        cls,
        building: Building,
        model_type: str = ForecastModelRun.ModelType.RANDOM_FOREST,
        horizon_days: int = 30,
        user=None
    ) -> ForecastModelRun:
        """Main entry point to train, validate, predict, and save a forecast run."""
        df = cls.load_building_dataframe(building)

        if len(df) < cls.MIN_REQUIRED_DAYS:
            raise ValueError(
                f"Building '{building.name}' requires at least {cls.MIN_REQUIRED_DAYS} days of readings. "
                f"Currently available: {len(df)} days."
            )

        run = ForecastModelRun.objects.create(
            building=building,
            model_type=model_type,
            horizon_days=horizon_days,
            created_by=user,
            status=ForecastModelRun.Status.PENDING,
        )

        try:
            # 1. Validation split (last 20% or max 14 days) to calculate test metrics
            val_size = min(max(7, int(len(df) * 0.2)), 30)
            train_df = df.iloc[:-val_size].copy()
            val_df = df.iloc[-val_size:].copy()

            # 2. Evaluate model performance on validation set
            metrics = cls._evaluate_model(train_df, val_df, model_type)
            run.r2_score = metrics["r2"]
            run.rmse = Decimal(f"{metrics['rmse']:.2f}")
            run.mae = Decimal(f"{metrics['mae']:.2f}")
            run.mape = Decimal(f"{metrics['mape']:.2f}")

            # 3. Retrain on full historical dataset and project future horizon
            predictions_df = cls._predict_future(df, model_type, horizon_days)

            # 4. Save forecasted values
            forecast_objects = []
            for _, row in predictions_df.iterrows():
                forecast_objects.append(
                    ForecastValue(
                        run=run,
                        forecast_date=row["date"].date(),
                        predicted_kwh=Decimal(f"{max(0, row['predicted_kwh']):.2f}"),
                        lower_bound_kwh=Decimal(f"{max(0, row['lower_bound']):.2f}"),
                        upper_bound_kwh=Decimal(f"{max(0, row['upper_bound']):.2f}"),
                    )
                )
            ForecastValue.objects.bulk_create(forecast_objects)

            run.status = ForecastModelRun.Status.COMPLETED
            run.save()
            return run

        except Exception as e:
            run.status = ForecastModelRun.Status.FAILED
            run.error_message = str(e)
            run.save()
            raise e

    @classmethod
    def _evaluate_model(cls, train_df: pd.DataFrame, val_df: pd.DataFrame, model_type: str) -> dict:
        full_df = pd.concat([train_df, val_df], ignore_index=True)
        feat_df = cls.generate_features(full_df).dropna()

        split_idx = len(train_df)
        train_feat = feat_df[feat_df["date"] < val_df["date"].min()]
        val_feat = feat_df[feat_df["date"] >= val_df["date"].min()]

        feature_cols = ["dayofweek", "month", "day", "is_weekend", "lag_1", "lag_7", "lag_14", "rolling_mean_7", "rolling_mean_14"]
        X_train, y_train = train_feat[feature_cols], train_feat["kwh_usage"]
        X_val, y_val = val_feat[feature_cols], val_feat["kwh_usage"]

        if model_type == ForecastModelRun.ModelType.RANDOM_FOREST:
            model = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=8)
        else:
            model = Ridge(alpha=1.0)

        model.fit(X_train, y_train)
        y_pred = model.predict(X_val)

        # Calculate metrics
        r2 = max(0.0, float(r2_score(y_val, y_pred)))
        rmse = float(np.sqrt(mean_squared_error(y_val, y_pred)))
        mae = float(mean_absolute_error(y_val, y_pred))
        
        # MAPE safe calculation (avoid division by zero)
        non_zero = y_val != 0
        if non_zero.any():
            mape = float(np.mean(np.abs((y_val[non_zero] - y_pred[non_zero]) / y_val[non_zero])) * 100)
        else:
            mape = 0.0

        return {"r2": r2, "rmse": rmse, "mae": mae, "mape": mape}

    @classmethod
    def _predict_future(cls, df: pd.DataFrame, model_type: str, horizon_days: int) -> pd.DataFrame:
        """Autoregressively roll forward to forecast future dates."""
        working_df = df.copy()
        feature_cols = ["dayofweek", "month", "day", "is_weekend", "lag_1", "lag_7", "lag_14", "rolling_mean_7", "rolling_mean_14"]

        # Train on full history
        feat_df = cls.generate_features(working_df).dropna()
        X = feat_df[feature_cols]
        y = feat_df["kwh_usage"]

        if model_type == ForecastModelRun.ModelType.RANDOM_FOREST:
            model = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=8)
        else:
            model = Ridge(alpha=1.0)

        model.fit(X, y)
        residuals = y - model.predict(X)
        std_error = np.std(residuals) if len(residuals) > 0 else (y.mean() * 0.1)

        # Roll forward day-by-day
        future_predictions = []
        last_date = working_df["date"].max()

        for step in range(1, horizon_days + 1):
            next_date = last_date + timedelta(days=step)
            # Create a provisional row
            temp_df = pd.concat([working_df, pd.DataFrame([{"date": next_date, "kwh_usage": np.nan}])], ignore_index=True)
            temp_feat = cls.generate_features(temp_df).iloc[[-1]]

            X_next = temp_feat[feature_cols]
            pred_kwh = float(model.predict(X_next)[0])
            pred_kwh = max(0.0, pred_kwh)

            # 95% Confidence Interval (z = 1.96, widening over horizon)
            uncertainty = 1.96 * std_error * np.sqrt(1 + (step / horizon_days))
            lower_bound = max(0.0, pred_kwh - uncertainty)
            upper_bound = pred_kwh + uncertainty

            future_predictions.append({
                "date": next_date,
                "predicted_kwh": pred_kwh,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
            })

            # Append the predicted point into working_df to feed into subsequent lags
            working_df = pd.concat([working_df, pd.DataFrame([{"date": next_date, "kwh_usage": pred_kwh}])], ignore_index=True)

        return pd.DataFrame(future_predictions)

    @classmethod
    def build_forecast_plot_html(cls, run: ForecastModelRun) -> str:
        """Generate an interactive Plotly chart with Historical Actuals, Predictions, and Confidence Bands."""
        # 1. Historical Actuals (Past 60 days)
        history_df = cls.load_building_dataframe(run.building)
        recent_history = history_df.tail(60)

        # 2. Forecast Values
        values = run.values.all().order_by("forecast_date")
        dates = [v.forecast_date for v in values]
        preds = [float(v.predicted_kwh) for v in values]
        lowers = [float(v.lower_bound_kwh) if v.lower_bound_kwh else float(v.predicted_kwh) for v in values]
        uppers = [float(v.upper_bound_kwh) if v.upper_bound_kwh else float(v.predicted_kwh) for v in values]

        fig = go.Figure()

        # Upper bound (hidden line for fill)
        fig.add_trace(go.Scatter(
            x=dates,
            y=uppers,
            mode='lines',
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip'
        ))

        # Lower bound with 95% CI fill
        fig.add_trace(go.Scatter(
            x=dates,
            y=lowers,
            mode='lines',
            line=dict(width=0),
            fill='tonexty',
            fillcolor='rgba(22, 163, 74, 0.15)',
            name='95% Confidence Band',
            hoverinfo='skip'
        ))

        # Historical Actual Line
        if not recent_history.empty:
            fig.add_trace(go.Scatter(
                x=recent_history["date"],
                y=recent_history["kwh_usage"],
                mode='lines+markers',
                name='Actual Consumption (Historical)',
                line=dict(color='#0f766e', width=2.5),
                marker=dict(size=4)
            ))

        # Forecasted Line
        fig.add_trace(go.Scatter(
            x=dates,
            y=preds,
            mode='lines+markers',
            name='Forecasted (Predicted kWh)',
            line=dict(color='#16a34a', width=3, dash='dash'),
            marker=dict(size=5, symbol='diamond')
        ))

        fig.update_layout(
            title=f"<b>{run.building.name}</b> — Energy Demand Forecast ({run.get_model_type_display()})",
            xaxis_title="Date",
            yaxis_title="Energy Usage (kWh)",
            hovermode="x unified",
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=30, t=80, b=40),
            font=dict(family="Inter, sans-serif", size=12),
        )

        return to_html(fig, full_html=False, include_plotlyjs="cdn", config={"responsive": True})
