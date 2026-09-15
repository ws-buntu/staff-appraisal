"""Disposable CI integration check. Run inside backend after migration/startup.

Creates and removes its own temporary account. Never use against a production DB.
Token contents and generated credentials are never printed.
"""

import json
import os
import secrets
from urllib.error import HTTPError
from urllib.request import Request, urlopen

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
from django.contrib.auth import get_user_model

django.setup()


def request(path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = Request(
        "http://127.0.0.1:8000/api/auth/" + path + "/",
        data=json.dumps(data).encode() if data is not None else None,
        headers=headers,
    )
    try:
        response = urlopen(req, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        body = response.read()
        return response.status, json.loads(body) if body else None


password = secrets.token_urlsafe(32)
user = get_user_model().objects.create_user(
    username="ci-smoke-" + secrets.token_hex(8), password=password
)
try:
    assert request("me")[0] == 401, "Anonymous account access must be denied"
    status, tokens = request("login", {"username": user.username, "password": password})
    assert status == 200, "Login failed"
    status, profile = request("me", token=tokens["access"])
    assert status == 200 and profile["id"] == str(user.pk), "Wrong current account"
    assert profile["role"] == "EMPLOYEE", "Unsafe default role"
    status, rotated = request("refresh", {"refresh": tokens["refresh"]})
    assert status == 200, "Refresh failed"
    assert request("refresh", {"refresh": tokens["refresh"]})[0] == 401, (
        "Old refresh token replayed"
    )
    assert request("logout", {"refresh": rotated["refresh"]}, rotated["access"])[0] == 204, (
        "Logout failed"
    )
    assert request("refresh", {"refresh": rotated["refresh"]})[0] == 401, (
        "Logged-out refresh accepted"
    )
    # Login and three refresh attempts above consume four shared throttle slots.
    assert request("login", {"username": user.username, "password": "incorrect"})[0] == 401, (
        "Fifth auth attempt failed unexpectedly"
    )
    assert request("login", {"username": user.username, "password": "incorrect"})[0] == 429, (
        "Shared Redis-backed auth quota was bypassed"
    )
    print("Authentication HTTP smoke passed: login, identity, rotation, logout, replay rejection.")
finally:
    user.delete()
