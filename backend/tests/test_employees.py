import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from employees.models import Department, Employee
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def records():
    User = get_user_model()
    users = {
        role: User.objects.create_user(username=role, role=role)
        for role in ["HR", "ADMIN", "HOD", "APPRAISER", "EMPLOYEE"]
    }
    users["other"] = User.objects.create_user(username="other")
    a = Department.objects.create(name="Finance", code="FIN")
    b = Department.objects.create(name="Operations", code="OPS")
    own = Employee.objects.create(
        user=users["EMPLOYEE"],
        staff_id="E1",
        surname="One",
        first_name="Employee",
        department=a,
        appraiser=users["APPRAISER"],
    )
    other = Employee.objects.create(
        user=users["other"], staff_id="E2", surname="Two", first_name="Other", department=b
    )
    Employee.objects.create(
        user=users["HOD"], staff_id="H1", surname="Head", first_name="Department", department=a
    )
    return users, a, b, own, other


def client(user=None):
    api = APIClient()
    if user:
        api.force_authenticate(user)
    return api


@pytest.mark.parametrize("path", ["/api/employees/", "/api/departments/"])
def test_auth_required(path):
    assert client().get(path).status_code == 401


@pytest.mark.parametrize(
    "role,expected", [("HR", 3), ("ADMIN", 3), ("HOD", 2), ("APPRAISER", 1), ("EMPLOYEE", 1)]
)
def test_scope_and_no_store(records, role, expected):
    users, a, b, own, other = records
    api = client(users[role])
    response = api.get("/api/employees/")
    assert response.status_code == 200
    assert response.data["count"] == expected
    assert "no-store" in response["Cache-Control"]
    assert api.get(f"/api/employees/{own.pk}/").status_code == 200
    assert api.get(f"/api/employees/{other.pk}/").status_code == (
        200 if role in ["HR", "ADMIN"] else 404
    )
    assert api.get("/api/departments/").data["count"] == (2 if role in ["HR", "ADMIN"] else 1)
    assert api.get(f"/api/departments/{b.pk}/").status_code == (
        200 if role in ["HR", "ADMIN"] else 404
    )


@pytest.mark.parametrize("role", ["HOD", "APPRAISER", "EMPLOYEE"])
def test_non_managers_cannot_write_even_superuser(records, role):
    users, a, b, own, other = records
    users[role].is_superuser = True
    users[role].save()
    api = client(users[role])
    for path in ["/api/employees/", "/api/departments/"]:
        assert api.post(path, {}, format="json").status_code == 403
    assert api.patch(f"/api/employees/{own.pk}/", {"surname": "Changed"}).status_code == 403
    assert api.patch(f"/api/departments/{a.pk}/", {"name": "Changed"}).status_code == 403


def test_hr_crud_and_binding_immutable(records):
    users, a, b, own, other = records
    api = client(users["HR"])
    response = api.post("/api/departments/", {"name": "New", "code": "NEW"})
    assert response.status_code == 201
    dept = response.data["id"]
    new_user = get_user_model().objects.create_user(username="new")
    data = {
        "user": str(new_user.pk),
        "staff_id": "N1",
        "surname": "Surname",
        "first_name": "Name",
        "department": dept,
        "gender": "Self-described",
        "appointment_date": "2020-01-01",
        "appraiser": str(users["APPRAISER"].pk),
    }
    response = api.post("/api/employees/", data, format="json")
    assert response.status_code == 201, response.data
    path = f"/api/employees/{response.data['id']}/"
    assert api.patch(path, {"is_active": False}, format="json").status_code == 200
    assert api.patch(path, {"user": str(users["HR"].pk)}, format="json").status_code == 400
    assert api.delete(path).status_code == 405
    assert api.delete(f"/api/departments/{dept}/").status_code == 405
    assert api.patch(f"/api/departments/{dept}/", {"code": "UPDATED"}).status_code == 200


@pytest.mark.parametrize(
    "field,value",
    [
        ("department", "bad-uuid"),
        ("department", "00000000-0000-0000-0000-000000000001"),
        ("appraiser", "bad-uuid"),
        ("appointment_date", "not-a-date"),
    ],
)
def test_invalid_references_and_dates(records, field, value):
    users, a, b, own, other = records
    response = client(users["HR"]).patch(f"/api/employees/{own.pk}/", {field: value})
    assert response.status_code == 400


def test_appraiser_validation_and_reassignment(records):
    users, a, b, own, other = records
    api = client(users["HR"])
    path = f"/api/employees/{own.pk}/"
    for user in [users["EMPLOYEE"], users["HR"], users["HOD"]]:
        assert api.patch(path, {"appraiser": str(user.pk)}).status_code == 400
    users["APPRAISER"].is_active = False
    users["APPRAISER"].save()
    assert api.patch(path, {"appraiser": str(users["APPRAISER"].pk)}).status_code == 400
    users["APPRAISER"].is_active = True
    users["APPRAISER"].save()
    assert (
        api.patch(path, {"appraiser": None, "department": str(b.pk)}, format="json").status_code
        == 200
    )
    assert client(users["APPRAISER"]).get(path).status_code == 404
    assert client(users["HOD"]).get(path).status_code == 404


def test_database_constraints_and_protected_references(records):
    users, a, b, own, other = records
    for changes in [{"staff_id": other.staff_id}, {"user": other.user}, {"appraiser": own.user}]:
        with pytest.raises(IntegrityError), transaction.atomic():
            Employee.objects.filter(pk=own.pk).update(**changes)
    for changes in [{"name": b.name}, {"code": b.code}]:
        with pytest.raises(IntegrityError), transaction.atomic():
            Department.objects.filter(pk=a.pk).update(**changes)
    for instance in [a, own.user, users["APPRAISER"]]:
        with pytest.raises(ProtectedError):
            instance.delete()


@pytest.mark.parametrize("role", ["EMPLOYEE", "APPRAISER", "HOD"])
def test_users_without_profile_or_assignments_see_nothing(role):
    user = get_user_model().objects.create_user(username="unlinked", role=role)
    api = client(user)
    assert api.get("/api/employees/").data["count"] == 0
    assert api.get("/api/departments/").data["count"] == 0


def test_appraiser_sees_own_profile_and_assigned_department(records):
    users, a, b, own, other = records
    profile = Employee.objects.create(
        user=users["APPRAISER"], staff_id="A1", surname="Reviewer", first_name="Name", department=b
    )
    api = client(users["APPRAISER"])
    assert api.get("/api/employees/").data["count"] == 2
    assert api.get(f"/api/employees/{profile.pk}/").status_code == 200
    assert api.get("/api/departments/").data["count"] == 2
    assert (
        client(users["HR"])
        .patch(f"/api/employees/{profile.pk}/", {"appraiser": str(users["APPRAISER"].pk)})
        .status_code
        == 400
    )


def test_nested_account_input_cannot_modify_roles(records):
    users, a, b, own, other = records
    api = client(users["HR"])
    response = api.patch(
        f"/api/employees/{own.pk}/",
        {"user": {"id": str(own.user_id), "role": "ADMIN"}},
        format="json",
    )
    assert response.status_code == 400
    own.user.refresh_from_db()
    assert own.user.role == "EMPLOYEE"


def test_unique_fields_and_invalid_user_are_api_errors(records):
    users, a, b, own, other = records
    api = client(users["HR"])
    assert api.patch(f"/api/departments/{a.pk}/", {"code": b.code}).status_code == 400
    assert api.patch(f"/api/departments/{a.pk}/", {"name": b.name}).status_code == 400
    assert api.patch(f"/api/employees/{own.pk}/", {"staff_id": other.staff_id}).status_code == 400
    data = {
        "user": "bad-uuid",
        "staff_id": "NEW",
        "surname": "New",
        "first_name": "New",
        "department": str(a.pk),
    }
    assert api.post("/api/employees/", data).status_code == 400
    data["user"] = str(own.user_id)
    assert api.post("/api/employees/", data).status_code == 400


def test_pagination_is_bounded_and_stable(records):
    users, a, b, own, other = records
    Department.objects.bulk_create(
        [Department(name=f"Department {i:03}", code=f"D{i:03}") for i in range(55)]
    )
    api = client(users["HR"])
    page = api.get("/api/departments/").data
    assert page["count"] == 57
    assert len(page["results"]) == 50
    assert page["next"]
    last = api.get("/api/departments/?page=2").data
    assert len(last["results"]) == 7
    assert not {row["id"] for row in page["results"]} & {row["id"] for row in last["results"]}


def test_admin_can_update_and_deactivate_employee(records):
    users, a, b, own, other = records
    api = client(users["ADMIN"])
    response = api.patch(f"/api/employees/{own.pk}/", {"is_active": False}, format="json")
    assert response.status_code == 200
    own.refresh_from_db()
    assert own.is_active is False
    # Directory retirement preserves identity and references for appraisal history.
    assert api.get(f"/api/employees/{own.pk}/").status_code == 200


def test_archived_employee_keeps_own_read_access_with_active_login(records):
    from rest_framework_simplejwt.tokens import RefreshToken

    users, a, b, own, other = records
    own.is_active = False
    own.save(update_fields=["is_active"])
    user = users["EMPLOYEE"]
    user.refresh_from_db()
    assert user.is_active
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION="Bearer " + str(RefreshToken.for_user(user).access_token))
    response = api.get(f"/api/employees/{own.pk}/")
    assert response.status_code == 200
    assert response.data["is_active"] is False
    assert api.get(f"/api/employees/{other.pk}/").status_code == 404
