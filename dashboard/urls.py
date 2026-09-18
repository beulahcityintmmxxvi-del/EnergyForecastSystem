from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('comparison/', views.comparison_dashboard, name='comparison_dashboard'),
]