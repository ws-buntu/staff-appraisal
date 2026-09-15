from django.db.models import Q
from django.utils.cache import patch_cache_control
from rest_framework import mixins, permissions, viewsets
from rest_framework.pagination import PageNumberPagination

from .models import Department, Employee
from .serializers import DepartmentSerializer, EmployeeSerializer


class DirectoryPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and (request.method in permissions.SAFE_METHODS or user.role in ["HR", "ADMIN"])
        )


class DirectoryPagination(PageNumberPagination):
    page_size = 50


def visible_employees(user):
    employees = Employee.objects.all()
    if user.role in ["HR", "ADMIN"]:
        return employees
    if user.role == "HOD":
        department = employees.filter(user=user).values("department_id")
        return employees.filter(department_id__in=department)
    if user.role == "APPRAISER":
        return employees.filter(Q(appraiser=user) | Q(user=user))
    return employees.filter(user=user)


class DirectoryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated, DirectoryPermission]
    pagination_class = DirectoryPagination

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        return response


class EmployeeViewSet(DirectoryViewSet):
    serializer_class = EmployeeSerializer

    def get_queryset(self):
        return visible_employees(self.request.user).select_related(
            "user", "department", "appraiser"
        )


class DepartmentViewSet(DirectoryViewSet):
    serializer_class = DepartmentSerializer

    def get_queryset(self):
        if self.request.user.role in ["HR", "ADMIN"]:
            return Department.objects.all()
        return Department.objects.filter(
            id__in=visible_employees(self.request.user).values("department_id")
        )
