from django.db import models


class Building(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class EnergyConsumption(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='energy_records')
    reading_date = models.DateField()
    meter_id = models.CharField(max_length=50, blank=True, null=True)
    consumption_kwh = models.DecimalField(max_digits=12, decimal_places=2)
    cost = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    peak_demand_kw = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-reading_date']

    def __str__(self):
        return f"{self.building.name} - {self.reading_date} - {self.consumption_kwh} kWh"