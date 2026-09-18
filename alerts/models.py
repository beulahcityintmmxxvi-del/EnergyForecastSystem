# alerts/models.py
from django.db import models

from energy.models import Building, EnergyConsumption


class BuildingThreshold(models.Model):
    building = models.OneToOneField(
        Building,
        on_delete=models.CASCADE,
        related_name="threshold",
    )
    monthly_threshold_kwh = models.DecimalField(
        max_digits=12, decimal_places=2, default=3000
    )
    spike_threshold_percent = models.DecimalField(
        max_digits=6, decimal_places=2, default=20
    )
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["building__name"]

    def __str__(self):
        return f"Threshold – {self.building}"


class EnergyAlert(models.Model):
    class AlertType(models.TextChoices):
        MONTHLY_THRESHOLD = "monthly_threshold", "Monthly Threshold Exceeded"
        DAILY_SPIKE = "daily_spike", "Daily Spike Detected"

    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"

    building = models.ForeignKey(
        Building,
        on_delete=models.CASCADE,
        related_name="alerts",
    )
    energy_record = models.ForeignKey(
        EnergyConsumption,
        on_delete=models.SET_NULL,
        related_name="alerts",
        blank=True,
        null=True,
    )
    alert_type = models.CharField(max_length=40, choices=AlertType.choices)
    severity = models.CharField(
        max_length=10, choices=Severity.choices, default=Severity.WARNING
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    alert_date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    resolved_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title}"


class ThresholdDefaults(models.Model):
    """
    Singleton row that stores the global default thresholds applied to
    newly created buildings.
    """

    monthly_threshold_kwh = models.DecimalField(
        max_digits=12, decimal_places=2, default=3000
    )
    spike_threshold_percent = models.DecimalField(
        max_digits=6, decimal_places=2, default=20
    )
    active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Threshold Defaults"
        verbose_name_plural = "Threshold Defaults"

    # ── Singleton enforcement ────────────────────────────────────
    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """Return the single row, creating it with defaults if needed."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Global Threshold Defaults"
