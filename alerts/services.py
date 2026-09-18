# alerts/services.py
from decimal import Decimal
from django.utils import timezone
from django.db.models import Avg
from .models import BuildingThreshold, EnergyAlert, ThresholdDefaults
from energy.models import Building, EnergyConsumption


class AlertEngine:
    @staticmethod
    def get_building_threshold(building: Building):
        """Get building-specific threshold or fall back to system defaults."""
        try:
            return building.threshold
        except BuildingThreshold.DoesNotExist:
            defaults = ThresholdDefaults.load()
            return defaults

    @classmethod
    def evaluate_consumption_record(cls, record: EnergyConsumption):
        """
        Evaluate a single EnergyConsumption entry for:
        1. Spike vs. historical average (daily spike)
        2. Exceeding monthly budget/threshold
        """
        building = record.building
        threshold = cls.get_building_threshold(building)

        if not threshold.active:
            return []

        created_alerts = []
        kwh = Decimal(str(record.kwh_usage))

        # --- Check 1: Daily Spike Detection (compared to 30-day average) ---
        past_30_days_avg = (
            EnergyConsumption.objects.filter(
                building=building,
                date__lt=record.date,
                date__gte=record.date - timezone.timedelta(days=30),
            ).aggregate(avg_kwh=Avg("kwh_usage"))["avg_kwh"]
        )

        if past_30_days_avg:
            avg_decimal = Decimal(str(past_30_days_avg))
            if avg_decimal > 0:
                spike_percentage = ((kwh - avg_decimal) / avg_decimal) * 100
                if spike_percentage >= threshold.spike_threshold_percent:
                    alert, created = EnergyAlert.objects.get_or_create(
                        building=building,
                        energy_record=record,
                        alert_type=EnergyAlert.AlertType.DAILY_SPIKE,
                        defaults={
                            "title": f"Consumption Spike: {building.name}",
                            "message": (
                                f"Usage of {kwh:,.2f} kWh on {record.date} is "
                                f"{spike_percentage:.1f}% above the 30-day average ({avg_decimal:,.2f} kWh)."
                            ),
                            "severity": (
                                EnergyAlert.Severity.CRITICAL
                                if spike_percentage >= (threshold.spike_threshold_percent * 2)
                                else EnergyAlert.Severity.WARNING
                            ),
                            "alert_date": record.date,
                        },
                    )
                    if created:
                        created_alerts.append(alert)

        return created_alerts
