# forecasting/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.forecast_dashboard, name="forecast_dashboard"),
    path("run/", views.run_forecast_view, name="run_forecast"),
    path("<int:pk>/", views.forecast_detail_view, name="forecast_detail"),
    path("building/<int:building_id>/", views.building_forecast_view, name="building_forecast"),
    path("<int:pk>/export/", views.export_forecast_csv, name="export_forecast_csv"),
]
