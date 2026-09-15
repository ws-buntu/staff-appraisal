import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def local_cache(settings):
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    cache.clear()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        username="employee", password="Good-test-password-93"
    )


def login(api, username="employee", password="Good-test-password-93"):
    return api.post("/api/auth/login/", {"username": username, "password": password})


def test_me_requires_authentication(api):
    assert api.get("/api/auth/me/").status_code == 401


@pytest.mark.django_db
def test_login_me_and_default_role(api, user):
    assert isinstance(user.pk, uuid.UUID)
    assert user.role == "EMPLOYEE"
    response = login(api)
    assert response.status_code == 200
    api.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])
    assert api.get("/api/auth/me/").json() == {
        "id": str(user.pk),
        "username": "employee",
        "first_name": "",
        "last_name": "",
        "email": "",
        "role": "EMPLOYEE",
    }


@pytest.mark.django_db
def test_invalid_credentials_do_not_issue_tokens(api, user):
    for username, password in [("employee", "incorrect"), ("missing", "incorrect")]:
        response = login(api, username, password)
        assert response.status_code == 401
        assert "access" not in response.data


@pytest.mark.django_db
def test_role_is_current_and_separate_from_django_flags(api, user):
    tokens = login(api).data
    user.role = "HR"
    user.save()
    api.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
    assert api.get("/api/auth/me/").data["role"] == "HR"
    user.refresh_from_db()
    assert not user.is_staff and not user.is_superuser
    user.is_superuser = True
    user.role = "EMPLOYEE"
    user.save()
    assert api.get("/api/auth/me/").data["role"] == "EMPLOYEE"


@pytest.mark.django_db
def test_database_rejects_unknown_role(user):
    with pytest.raises(IntegrityError), transaction.atomic():
        get_user_model().objects.filter(pk=user.pk).update(role="UNKNOWN")


@pytest.mark.django_db
def test_inactive_user_cannot_login_use_access_or_refresh(api, user):
    tokens = login(api).data
    user.is_active = False
    user.save()
    assert login(api).status_code == 401
    api.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
    assert api.get("/api/auth/me/").status_code == 401
    api.credentials()
    assert api.post("/api/auth/refresh/", {"refresh": tokens["refresh"]}).status_code == 401


@pytest.mark.django_db
def test_refresh_rotates_and_prevents_replay(api, user):
    tokens = login(api).data
    response = api.post("/api/auth/refresh/", {"refresh": tokens["refresh"]})
    assert response.status_code == 200
    assert response.data["refresh"] != tokens["refresh"]
    assert api.post("/api/auth/refresh/", {"refresh": tokens["refresh"]}).status_code == 401
    assert api.post("/api/auth/refresh/", {"refresh": response.data["refresh"]}).status_code == 200


@pytest.mark.django_db
def test_logout_revokes_owned_refresh_but_access_expires_normally(api, user):
    tokens = login(api).data
    assert api.post("/api/auth/logout/", {"refresh": tokens["refresh"]}).status_code == 401
    api.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
    assert api.post("/api/auth/logout/", {"refresh": tokens["refresh"]}).status_code == 204
    assert api.get("/api/auth/me/").status_code == 200
    api.credentials()
    assert api.post("/api/auth/refresh/", {"refresh": tokens["refresh"]}).status_code == 401


@pytest.mark.django_db
def test_logout_cannot_revoke_another_users_refresh(api, user):
    mine = login(api).data
    get_user_model().objects.create_user(username="other", password="Good-test-password-93")
    other = login(api, "other").data
    api.credentials(HTTP_AUTHORIZATION="Bearer " + mine["access"])
    assert api.post("/api/auth/logout/", {"refresh": other["refresh"]}).status_code == 403
    api.credentials()
    assert api.post("/api/auth/refresh/", {"refresh": other["refresh"]}).status_code == 200


@pytest.mark.django_db
def test_malformed_tokens_denied(api, user):
    tokens = login(api).data
    for value in ["broken", tokens["refresh"], tokens["access"][:-8] + "tampered"]:
        api.credentials(HTTP_AUTHORIZATION="Bearer " + value)
        assert api.get("/api/auth/me/").status_code == 401
    api.credentials()
    assert api.post("/api/auth/refresh/", {"refresh": "broken"}).status_code == 401


@pytest.mark.django_db
def test_login_throttle_limits_repeated_attempts(api):
    results = [login(api, "missing", "wrong").status_code for _ in range(6)]
    assert results == [401, 401, 401, 401, 401, 429]


@pytest.mark.django_db
def test_profile_is_read_only_and_registration_absent(api, user):
    tokens = login(api).data
    api.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
    assert api.patch("/api/auth/me/", {"role": "ADMIN"}).status_code == 405
    assert api.post("/api/auth/register/", {"username": "new"}).status_code == 404


@pytest.mark.django_db(transaction=True)
def test_concurrent_refresh_is_single_use():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections
    from rest_framework_simplejwt.tokens import RefreshToken

    user = get_user_model().objects.create_user(username="concurrent", password="test-password")
    refresh = str(RefreshToken.for_user(user))
    barrier = Barrier(2)

    def renew():
        close_old_connections()
        try:
            barrier.wait()
            return APIClient().post("/api/auth/refresh/", {"refresh": refresh}).status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: renew(), range(2)))
    assert sorted(results) == [200, 401]


@pytest.mark.django_db
def test_deleted_user_refresh_is_denied(api, user):
    tokens = login(api).data
    user.delete()
    assert api.post("/api/auth/refresh/", {"refresh": tokens["refresh"]}).status_code == 401


@pytest.mark.django_db
def test_login_throttle_ignores_untrusted_forwarded_header(api):
    results = [
        api.post(
            "/api/auth/login/",
            {"username": "missing", "password": "wrong"},
            HTTP_X_FORWARDED_FOR=f"192.0.2.{i}",
        ).status_code
        for i in range(6)
    ]
    assert results == [401, 401, 401, 401, 401, 429]


@pytest.mark.django_db
def test_password_change_revokes_access_and_refresh(api, user):
    tokens = login(api).data
    user.set_password("Changed-password-839")
    user.save()
    api.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
    assert api.get("/api/auth/me/").status_code == 401
    api.credentials()
    assert api.post("/api/auth/refresh/", {"refresh": tokens["refresh"]}).status_code == 401
    assert login(api, password="Changed-password-839").status_code == 200


@pytest.mark.django_db
def test_auth_responses_are_not_cacheable(api, user):
    response = login(api)
    assert "no-store" in response.headers.get("Cache-Control", "")
    api.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])
    assert "no-store" in api.get("/api/auth/me/").headers.get("Cache-Control", "")


@pytest.mark.django_db
def test_logout_rechecks_refresh_after_concurrent_rotation(api, user):
    from unittest.mock import patch

    from rest_framework_simplejwt.tokens import RefreshToken

    tokens = login(api).data
    api.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
    first = True

    def rotate_between_checks(value):
        nonlocal first
        token = RefreshToken(value)
        if first:
            first = False
            # Model a refresh that commits after logout's initial token validation.
            response = APIClient().post("/api/auth/refresh/", {"refresh": value})
            assert response.status_code == 200
        return token

    with patch("accounts.views.RefreshToken", side_effect=rotate_between_checks):
        assert api.post("/api/auth/logout/", {"refresh": tokens["refresh"]}).status_code == 401


@pytest.mark.django_db
def test_expired_tokens_are_rejected(api, user):
    from datetime import timedelta

    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    access.set_exp(lifetime=timedelta(seconds=-1))
    refresh.set_exp(lifetime=timedelta(seconds=-1))
    api.credentials(HTTP_AUTHORIZATION="Bearer " + str(access))
    assert api.get("/api/auth/me/").status_code == 401
    api.credentials()
    assert api.post("/api/auth/refresh/", {"refresh": str(refresh)}).status_code == 401


@pytest.mark.django_db
def test_login_cannot_assign_role_or_admin_flags(api, user):
    response = api.post(
        "/api/auth/login/",
        {
            "username": user.username,
            "password": "Good-test-password-93",
            "role": "ADMIN",
            "is_staff": True,
            "is_superuser": True,
        },
        format="json",
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.role == "EMPLOYEE"
    assert not user.is_staff and not user.is_superuser
