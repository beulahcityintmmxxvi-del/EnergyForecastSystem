from django.contrib import admin
from .models import Building, EnergyConsumption


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')


@admin.register(EnergyConsumption)
class EnergyConsumptionAdmin(admin.ModelAdmin):
    list_display = ('building', 'reading_date', 'meter_id', 'consumption_kwh', 'cost')
    list_filter = ('building', 'reading_date')
    search_fields = ('building__name', 'meter_id')
    date_hierarchy = 'reading_date'