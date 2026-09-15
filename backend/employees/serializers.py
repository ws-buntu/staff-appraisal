from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Department, Employee


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "code", "is_active"]
        read_only_fields = ["id"]


class EmployeeSerializer(serializers.ModelSerializer):
    appraiser = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.filter(is_active=True, role="APPRAISER"),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Employee
        fields = [
            "id",
            "user",
            "staff_id",
            "surname",
            "first_name",
            "other_names",
            "gender",
            "position",
            "grade_level",
            "division",
            "appointment_date",
            "department",
            "appraiser",
            "is_active",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if self.instance and "user" in attrs and attrs["user"].pk != self.instance.user_id:
            raise serializers.ValidationError({"user": "The linked account cannot be changed."})
        user = attrs.get("user", self.instance.user if self.instance else None)
        appraiser = attrs.get("appraiser", self.instance.appraiser if self.instance else None)
        if user and appraiser and user.pk == appraiser.pk:
            raise serializers.ValidationError(
                {"appraiser": "An employee cannot appraise themselves."}
            )
        return attrs
