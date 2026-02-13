"""URL configuration for fiscal app."""

from django.shortcuts import redirect
from django.urls import path

from . import views

urlpatterns = [
    path("", lambda r: redirect("dashboard")),
    path("register/", views.device_register, name="device_register"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("api/dashboard/status/", views.dashboard_status_api, name="dashboard_status_api"),
    path("api/fdms/status/", views.api_fdms_status, name="api_fdms_status"),
    path("api/open-day/", views.open_day_api, name="open_day_api"),
    path("api/close-day/", views.close_day_api, name="close_day_api"),
    path("logs/", views.fdms_logs, name="fdms_logs"),
]
