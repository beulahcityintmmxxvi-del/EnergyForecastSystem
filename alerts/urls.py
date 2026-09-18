from django.urls import path
from . import views

urlpatterns = [
    path('', views.alerts_dashboard, name='alerts_dashboard'),
    path('list/', views.alert_list, name='alert_list'),
    path('scan/', views.scan_alerts, name='scan_alerts'),
    path('resolve/<int:pk>/', views.resolve_alert, name='resolve_alert'),
    path('thresholds/', views.threshold_list, name='threshold_list'),
    path('thresholds/add/', views.threshold_create, name='threshold_create'),
    path('thresholds/<int:pk>/edit/', views.threshold_update, name='threshold_update'),
    path('threshold-defaults/', views.threshold_defaults, name='threshold_defaults'),
]