"""HTTP directory isolation check for disposable CI databases only."""

import json
import os
import secrets
from urllib.error import HTTPError
from urllib.request import Request, urlopen

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
from django.apps import apps
from django.contrib.auth import get_user_model

django.setup()


def check_directory():
    from rest_framework_simplejwt.tokens import RefreshToken

    employee_model = apps.get_model("employees", "Employee")
    department_model = apps.get_model("employees", "Department")
    suffix = secrets.token_hex(8)
    users = []
    employee_ids = []
    department_ids = []

    def api(path, token=None, data=None, method=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = Request(
            os.getenv("APPRAISAL_TEST_BASE_URL", "http://127.0.0.1:8000") + "/api/" + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers=headers,
            method=method,
        )
        try:
            response = urlopen(req, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None, response.headers

    def actor(label, role):
        user = get_user_model().objects.create_user(
            username=f"directory-ci-{label}-{suffix}", role=role
        )
        users.append(user)
        # Login is checked separately. Issue valid credentials for these disposable
        # accounts without consuming the shared login-throttle test's quota.
        return user, str(RefreshToken.for_user(user).access_token)

    try:
        _, hr_token = actor("hr", "HR")
        employee, employee_token = actor("employee", "EMPLOYEE")
        other, _ = actor("other", "EMPLOYEE")
        appraiser, appraiser_token = actor("appraiser", "APPRAISER")
        hod, hod_token = actor("hod", "HOD")
        assert api("employees/")[0] == 401
        for label in ["A", "B"]:
            status, data, _ = api(
                "departments/",
                hr_token,
                {"name": f"CI department {label} {suffix}", "code": f"{label}-{suffix}"},
            )
            assert status == 201, "HR department creation failed"
            department_ids.append(data["id"])
        for user, department, assigned in [
            (employee, department_ids[0], str(appraiser.pk)),
            (other, department_ids[1], None),
            (hod, department_ids[0], None),
        ]:
            status, data, _ = api(
                "employees/",
                hr_token,
                {
                    "user": str(user.pk),
                    "staff_id": f"ci-{len(employee_ids)}-{suffix}",
                    "surname": "Test",
                    "first_name": "Disposable",
                    "department": department,
                    "appraiser": assigned,
                },
            )
            assert status == 201, "HR employee creation failed"
            employee_ids.append(data["id"])
        for token, expected in [
            (employee_token, {employee_ids[0]}),
            (appraiser_token, {employee_ids[0]}),
            (hod_token, {employee_ids[0], employee_ids[2]}),
        ]:
            status, data, headers = api("employees/", token)
            assert status == 200 and {row["id"] for row in data["results"]} == expected
            assert "no-store" in headers.get("Cache-Control", "")
            assert api(f"employees/{employee_ids[1]}/", token)[0] == 404
            assert (
                api(f"employees/{employee_ids[0]}/", token, {"position": "Changed"}, "PATCH")[0]
                == 403
            )
        assert (
            api(f"employees/{employee_ids[0]}/", hr_token, {"user": str(other.pk)}, "PATCH")[0]
            == 400
        )
        assert api(f"employees/{employee_ids[0]}/", hr_token, method="DELETE")[0] == 405
        assert (
            api(f"employees/{employee_ids[0]}/", hr_token, {"appraiser": None}, "PATCH")[0] == 200
        )
        assert api(f"employees/{employee_ids[0]}/", appraiser_token)[0] == 404
        print(
            "Directory HTTP checks passed: HR management, role isolation, immutable ownership, reassignment."
        )
    finally:
        employee_model.objects.filter(pk__in=employee_ids).delete()
        department_model.objects.filter(pk__in=department_ids).delete()
        for user in reversed(users):
            user.delete()


check_directory()
