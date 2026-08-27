from __future__ import annotations

from rest_framework.permissions import BasePermission

from .access import is_faculty
from .access import is_hod
from .access import is_student


class IsHOD(BasePermission):
    def has_permission(self, request, view):
        return is_hod(request.user)


class IsFaculty(BasePermission):
    def has_permission(self, request, view):
        return is_faculty(request.user)


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return is_student(request.user)


class IsHODOrFaculty(BasePermission):
    def has_permission(self, request, view):
        return is_hod(request.user) or is_faculty(request.user)
