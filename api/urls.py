from django.urls import path
from . import views

urlpatterns = [
    path("summary/", views.api_summary, name="api_summary"),
    path("buildings/", views.api_buildings, name="api_buildings"),
    path("records/", views.api_records, name="api_records"),
]