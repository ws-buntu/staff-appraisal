from unittest.mock import patch

from django.db import OperationalError
from redis.exceptions import ConnectionError


def test_liveness_does_not_require_database(client):
    response = client.get("/api/health/live/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_checks_both_dependencies(client):
    with (
        patch("config.health.connection.cursor"),
        patch("config.health.Redis.from_url") as redis,
    ):
        redis.return_value.__enter__.return_value.ping.return_value = True
        response = client.get("/api/health/ready/")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"postgres": "ok", "redis": "ok"},
    }


def test_readiness_reports_database_failure_without_leaking_details(client):
    with (
        patch("config.health.connection.cursor", side_effect=OperationalError("secret")),
        patch("config.health.Redis.from_url"),
    ):
        response = client.get("/api/health/ready/")
    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "checks": {"postgres": "unavailable", "redis": "ok"},
    }


def test_readiness_reports_redis_failure(client):
    with (
        patch("config.health.connection.cursor"),
        patch("config.health.Redis.from_url") as redis,
    ):
        redis.return_value.__enter__.return_value.ping.side_effect = ConnectionError("secret")
        response = client.get("/api/health/ready/")
    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "checks": {"postgres": "ok", "redis": "unavailable"},
    }
