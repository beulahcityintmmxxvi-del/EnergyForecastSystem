from django.db import models
from energy.models import Building


class ForecastRun(models.Model):
    building = models.ForeignKey(
        Building,
        on_delete=models.CASCADE,
        related_name="forecast_runs"
    )

    generated_at = models.DateTimeField(auto_now_add=True)

    periods = models.IntegerField(default=30)

    mae = models.FloatField(null=True, blank=True)
    rmse = models.FloatField(null=True, blank=True)
    mape = models.FloatField(null=True, blank=True)
    accuracy = models.FloatField(null=True, blank=True)

    created_by = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f"{self.building.name} Forecast {self.generated_at:%Y-%m-%d}"
        

class ForecastResult(models.Model):
    forecast_run = models.ForeignKey(
        ForecastRun,
        on_delete=models.CASCADE,
        related_name='results'
    )

    forecast_date = models.DateField()

    predicted_consumption = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    lower_bound = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    upper_bound = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['forecast_date']

    def __str__(self):
        return f"{self.forecast_date} - {self.predicted_consumption}"
