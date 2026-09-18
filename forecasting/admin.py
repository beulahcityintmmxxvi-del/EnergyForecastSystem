# forecasting/admin.py
from django.contrib import admin
from .models import ForecastResult, ForecastRun


class ForecastResultInline(admin.TabularInline):
    model = ForecastResult
    extra = 0
    readonly_fields = ("forecast_date", "predicted_consumption", "lower_bound", "upper_bound")
    can_delete = False


@admin.register(ForecastRun)
class ForecastRunAdmin(admin.ModelAdmin):
    list_display = ("building", "periods", "mape", "accuracy", "rmse", "mae", "generated_at")
    list_filter = ("building",)
    search_fields = ("building__name",)
    readonly_fields = ("generated_at", "mae", "rmse", "mape", "accuracy")
    inlines = [ForecastResultInline]
