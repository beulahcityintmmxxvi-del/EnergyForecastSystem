import decimal
from datetime import date

from django.db.models import Sum

from ..models import BuildingThreshold, EnergyAlert, ThresholdDefaults


def get_or_create_threshold(building):
    defaults = ThresholdDefaults.load()
    threshold, _ = BuildingThreshold.objects.get_or_create(
        building=building,
        defaults={
            'monthly_threshold_kwh': defaults.monthly_threshold_kwh,
            'spike_threshold_percent': defaults.spike_threshold_percent,
            'active': defaults.active,
        }
    )
    return threshold


def evaluate_record_alerts(record):
    """
    Evaluate a newly created/updated energy record and create alerts if needed.
    Returns a list of created alerts.
    """
    created_alerts = []
    threshold = get_or_create_threshold(record.building)

    if not threshold.active:
        return created_alerts

    # Monthly threshold check
    month_start = date(record.reading_date.year, record.reading_date.month, 1)
    monthly_total = (
        record.building.energy_records
        .filter(reading_date__year=record.reading_date.year, reading_date__month=record.reading_date.month)
        .aggregate(total=Sum('consumption_kwh'))['total'] or decimal.Decimal('0')
    )
    monthly_total = decimal.Decimal(str(monthly_total))

    if monthly_total > threshold.monthly_threshold_kwh:
        existing = EnergyAlert.objects.filter(
            building=record.building,
            alert_type='monthly_threshold',
            alert_date=month_start,
            status='open'
        ).first()

        if not existing:
            alert = EnergyAlert.objects.create(
                building=record.building,
                energy_record=record,
                alert_type='monthly_threshold',
                severity='critical',
                title=f"{record.building.name} monthly consumption exceeded threshold",
                message=(
                    f"Monthly consumption for {record.building.name} in "
                    f"{record.reading_date.strftime('%B %Y')} is {monthly_total:,.2f} kWh, "
                    f"which exceeds the threshold of {threshold.monthly_threshold_kwh:,.2f} kWh."
                ),
                alert_date=month_start,
            )
            created_alerts.append(alert)

    # Spike detection compared to previous record
    previous_record = (
        record.building.energy_records
        .filter(reading_date__lt=record.reading_date)
        .order_by('-reading_date', '-id')
        .first()
    )

    if previous_record and previous_record.consumption_kwh and previous_record.consumption_kwh > 0:
        current = decimal.Decimal(str(record.consumption_kwh))
        previous = decimal.Decimal(str(previous_record.consumption_kwh))

        percent_change = ((current - previous) / previous) * decimal.Decimal('100')

        if percent_change >= threshold.spike_threshold_percent:
            existing = EnergyAlert.objects.filter(
                building=record.building,
                alert_type='daily_spike',
                alert_date=record.reading_date,
                status='open'
            ).first()

            if not existing:
                severity = (
                    'critical'
                    if percent_change >= (threshold.spike_threshold_percent * decimal.Decimal('2'))
                    else 'warning'
                )
                alert = EnergyAlert.objects.create(
                    building=record.building,
                    energy_record=record,
                    alert_type='daily_spike',
                    severity=severity,
                    title=f"{record.building.name} consumption spike detected",
                    message=(
                        f"Consumption increased by {percent_change:.2f}% compared with the "
                        f"previous reading ({previous:,.2f} kWh to {current:,.2f} kWh)."
                    ),
                    alert_date=record.reading_date,
                )
                created_alerts.append(alert)

    return created_alerts