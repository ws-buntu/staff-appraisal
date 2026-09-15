from django.urls import include, path

from .health import live, ready

urlpatterns = [
    path("api/auth/", include("accounts.urls")),
    path("api/health/live/", live),
    path("api/health/ready/", ready),
]
