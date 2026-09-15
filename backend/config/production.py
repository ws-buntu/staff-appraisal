"""Opt-in deployment settings; select with DJANGO_SETTINGS_MODULE=config.production."""

import os

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F403
from .settings import MIDDLEWARE, SECRET_KEY

if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be a strong generated secret.")

if os.getenv("DJANGO_DEBUG", "false").lower() != "false":
    raise ImproperlyConfigured("DJANGO_DEBUG must be false in production.")

ALLOWED_HOSTS = [
    host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if host.strip()
]
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must explicitly name deployment hosts.")

DEBUG = False
MIDDLEWARE = [
    *MIDDLEWARE,
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# Enable HSTS only after HTTPS works on the actual deployment host. Keep broader
# subdomain coverage and preload opt-in to avoid affecting unrelated services.
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_HSTS_SECONDS", "0"))
if SECURE_HSTS_SECONDS < 0:
    raise ImproperlyConfigured("DJANGO_HSTS_SECONDS cannot be negative.")
SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    os.getenv("DJANGO_HSTS_INCLUDE_SUBDOMAINS", "false").lower() == "true"
)
SECURE_HSTS_PRELOAD = os.getenv("DJANGO_HSTS_PRELOAD", "false").lower() == "true"

# Deliberately do not trust client-supplied proxy headers. A trusted TLS proxy
# integration must strip and set forwarded headers before configuring that here.
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
