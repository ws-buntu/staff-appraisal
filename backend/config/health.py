from django.conf import settings
from django.db import DatabaseError, connection
from redis import Redis
from redis.exceptions import RedisError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def live(request):
    return Response({"status": "ok"})


@api_view(["GET"])
@permission_classes([AllowAny])
def ready(request):
    checks = {"postgres": "ok", "redis": "ok"}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        checks["postgres"] = "unavailable"
    try:
        with Redis.from_url(
            settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2
        ) as redis:
            redis.ping()
    except RedisError:
        checks["redis"] = "unavailable"
    available = all(value == "ok" for value in checks.values())
    return Response(
        {"status": "ready" if available else "unavailable", "checks": checks},
        status=200 if available else 503,
    )
