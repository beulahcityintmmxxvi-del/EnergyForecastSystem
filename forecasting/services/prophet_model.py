import numpy as np
import pandas as pd
from django.db.models import Sum
from energy.models import EnergyConsumption

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    Prophet = None
    PROPHET_AVAILABLE = False


def build_timeseries(building=None):
    """
    Build a daily time-series DataFrame with columns:
    ds = date
    y  = total energy consumption
    """
    qs = EnergyConsumption.objects.all()

    if building:
        qs = qs.filter(building=building)

    rows = (
        qs.values('reading_date')
        .annotate(y=Sum('consumption_kwh'))
        .order_by('reading_date')
    )

    df = pd.DataFrame.from_records(rows)

    if df.empty:
        return df

    df = df.rename(columns={'reading_date': 'ds'})
    df['ds'] = pd.to_datetime(df['ds'])
    df['y'] = pd.to_numeric(df['y'], errors='coerce').fillna(0.0).astype(float)

    return df[['ds', 'y']]


def forecast_consumption(df, periods=30):
    """
    Train Prophet and forecast future consumption.
    """
    if not PROPHET_AVAILABLE:
        raise ImportError("Prophet is not installed. Install it with: pip install prophet")

    if df.empty:
        raise ValueError("No historical data available.")

    if len(df) < 3:
        raise ValueError("At least 3 data points are required for forecasting.")

    model = Prophet(
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=True
    )

    model.fit(df)

    future = model.make_future_dataframe(periods=periods, freq='D')
    forecast = model.predict(future)

    return model, forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]


def evaluate_forecast(df, test_size=30):
    """
    Evaluate Prophet forecast on a hold-out set using MAE, RMSE, MAPE.
    Returns: model, evaluation_df, metrics_dict
    """
    if not PROPHET_AVAILABLE:
        raise ImportError("Prophet is not installed. Install it with: pip install prophet")

    if df.empty:
        raise ValueError("No historical data available.")

    df = df.sort_values('ds').reset_index(drop=True)

    if len(df) < 6:
        raise ValueError("At least 6 data points are required for forecast evaluation.")

    test_size = int(test_size)
    test_size = max(1, min(test_size, len(df) - 3))

    train = df.iloc[:-test_size].copy()
    test = df.iloc[-test_size:].copy()

    if len(train) < 3:
        raise ValueError("Not enough training data for evaluation.")

    model = Prophet(
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=True
    )

    model.fit(train)

    future = pd.DataFrame({'ds': test['ds']})
    forecast = model.predict(future)

    evaluation_df = pd.DataFrame({
        'ds': test['ds'].values,
        'actual': test['y'].astype(float).values,
        'predicted': forecast['yhat'].astype(float).values,
        'lower_bound': forecast['yhat_lower'].astype(float).values,
        'upper_bound': forecast['yhat_upper'].astype(float).values,
    })

    actual = evaluation_df['actual'].to_numpy(dtype=float)
    predicted = evaluation_df['predicted'].to_numpy(dtype=float)
    errors = actual - predicted

    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(np.square(errors))))

    non_zero = actual != 0
    if np.any(non_zero):
        mape = float(np.mean(np.abs(errors[non_zero] / actual[non_zero])) * 100)
        accuracy = float(max(0, 100 - mape))
    else:
        mape = None
        accuracy = None

    metrics = {
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'accuracy': accuracy,
    }

    return model, evaluation_df, metrics