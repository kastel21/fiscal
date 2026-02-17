"""URL configuration for legal app."""

from django.urls import path

from . import views

urlpatterns = [
    path("eula/", views.eula_view, name="eula"),
    path("privacy/", views.privacy_view, name="privacy"),
]
