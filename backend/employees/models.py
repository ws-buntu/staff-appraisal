import uuid

from django.conf import settings
from django.db import models


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=40, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "id"]


class Employee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="employee"
    )
    staff_id = models.CharField(max_length=60, unique=True)
    surname = models.CharField(max_length=150)
    first_name = models.CharField(max_length=150)
    other_names = models.CharField(max_length=200, blank=True)
    gender = models.CharField(max_length=100, blank=True)
    position = models.CharField(max_length=200, blank=True)
    grade_level = models.CharField(max_length=100, blank=True)
    division = models.CharField(max_length=200, blank=True)
    appointment_date = models.DateField(null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="employees")
    appraiser = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_employees",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["staff_id", "id"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(user=models.F("appraiser")),
                name="employee_appraiser_not_self",
            )
        ]
