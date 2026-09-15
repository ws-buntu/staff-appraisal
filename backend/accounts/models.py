import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        EMPLOYEE = "EMPLOYEE", "Employee"
        APPRAISER = "APPRAISER", "Appraiser"
        HOD = "HOD", "Head of department"
        HR = "HR", "Human resources"
        ADMIN = "ADMIN", "Administrator"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.EMPLOYEE)

    class Meta(AbstractUser.Meta):
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=["EMPLOYEE", "APPRAISER", "HOD", "HR", "ADMIN"]),
                name="accounts_user_valid_role",
            )
        ]
