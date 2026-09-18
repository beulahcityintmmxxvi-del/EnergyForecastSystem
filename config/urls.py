from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('energy/', include('energy.urls')),
    path('forecasting/', include('forecasting.urls')),
    path('alerts/', include('alerts.urls')),
    path('reports/', include('reports.urls')),
    path('api/', include('api.urls')),
]