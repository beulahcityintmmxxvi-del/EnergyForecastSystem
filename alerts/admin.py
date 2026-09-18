# alerts/admin.py
from django.contrib import admin

from .models import BuildingThreshold, EnergyAlert, ThresholdDefaults


@admin.register(BuildingThreshold)
class BuildingThresholdAdmin(admin.ModelAdmin):
    list_display = (
        "building",
        "monthly_threshold_kwh",
        "spike_threshold_percent",
        "active",
        "updated_at",
    )
    list_filter = ("active",)
    search_fields = ("building__name", "building__code")
    ordering = ("building__name",)


@admin.register(EnergyAlert)
class EnergyAlertAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "building",
        "alert_type",
        "severity",
        "status",
        "alert_date",
        "created_at",
    )
    list_filter = ("status", "severity", "alert_type", "alert_date")
    search_fields = ("title", "message", "building__name", "building__code")
    ordering = ("-created_at",)


@admin.register(ThresholdDefaults)
class ThresholdDefaultsAdmin(admin.ModelAdmin):
    list_display = (
        "monthly_threshold_kwh",
        "spike_threshold_percent",
        "active",
        "updated_at",
    )

    def has_add_permission(self, request):
        # Prevent creating a second row in the admin.
        if ThresholdDefaults.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False
