import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]


def production_check(**changes):
    env = os.environ.copy()
    env.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.production",
            "DJANGO_SECRET_KEY": "test-only-" + "aB9xQ7rT2uV4wY6z" * 4,
            "DJANGO_ALLOWED_HOSTS": "appraisal.example.org",
            "POSTGRES_PASSWORD": "disposable-test-password",
            "DJANGO_HSTS_SECONDS": "31536000",
            "DJANGO_HSTS_INCLUDE_SUBDOMAINS": "true",
            "DJANGO_HSTS_PRELOAD": "true",
        }
    )
    env.update(changes)
    return subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
    )


def test_production_deployment_checks_pass_with_explicit_configuration():
    result = production_check()
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"DJANGO_SECRET_KEY": "short"}, "DJANGO_SECRET_KEY"),
        ({"DJANGO_ALLOWED_HOSTS": ""}, "DJANGO_ALLOWED_HOSTS"),
        ({"DJANGO_ALLOWED_HOSTS": "*"}, "DJANGO_ALLOWED_HOSTS"),
        ({"DJANGO_DEBUG": "true"}, "DJANGO_DEBUG"),
    ],
)
def test_production_rejects_unsafe_configuration(changes, message):
    result = production_check(**changes)
    assert result.returncode != 0
    assert message in result.stderr


def test_https_redirect_and_security_headers():
    env = os.environ.copy()
    env.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.production",
            "DJANGO_SECRET_KEY": "test-only-" + "aB9xQ7rT2uV4wY6z" * 4,
            "DJANGO_ALLOWED_HOSTS": "testserver",
            "POSTGRES_PASSWORD": "disposable-test-password",
            "DJANGO_DEBUG": "false",
        }
    )
    code = """
import django
django.setup()
from django.test import Client
client = Client()
redirect = client.get('/api/health/live/')
assert redirect.status_code == 301
assert redirect['Location'] == 'https://testserver/api/health/live/'
response = client.get('/api/health/live/', secure=True)
assert response.status_code == 200
assert response['X-Frame-Options'] == 'DENY'
assert response['X-Content-Type-Options'] == 'nosniff'
assert response['Referrer-Policy'] == 'strict-origin-when-cross-origin'
"""
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=BACKEND, env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
