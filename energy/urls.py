from django.urls import path
from . import views

urlpatterns = [
    path('buildings/', views.building_list, name='building_list'),
    path('buildings/add/', views.building_create, name='building_create'),
    path('buildings/<int:pk>/', views.building_detail, name='building_detail'),
    path('buildings/<int:pk>/edit/', views.building_update, name='building_update'),
    path('buildings/<int:pk>/delete/', views.building_delete, name='building_delete'),

    path('records/', views.energy_list, name='energy_list'),
    path('records/add/', views.energy_create, name='energy_create'),
    path('records/import/', views.energy_import, name='energy_import'),
    path('records/<int:pk>/edit/', views.energy_update, name='energy_update'),
    path('records/<int:pk>/delete/', views.energy_delete, name='energy_delete'),
]