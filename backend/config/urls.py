from django.urls import path

from .health import live, ready

urlpatterns = [path("api/health/live/", live), path("api/health/ready/", ready)]
