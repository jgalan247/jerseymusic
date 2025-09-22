from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('plans/', views.plans, name='plans'),
    path('subscribe/<int:plan_id>/', views.subscribe, name='subscribe'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
