from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from be_logbook.academics.models import AcademicYear
from be_logbook.academics.models import Department
from be_logbook.users.api.serializers import FacultyCreateSerializer
from be_logbook.users.api.serializers import StudentCreateSerializer
from be_logbook.users.api.serializers import UserSummarySerializer
from be_logbook.users.models import User
from be_logbook.users.services import UserService
from be_logbook.utils.permissions import IsHOD


class UserManagementViewSet(ModelViewSet):
    queryset = User.objects.all().select_related("student_profile", "faculty_profile")
    serializer_class = UserSummarySerializer
    permission_classes = [IsHOD]
    filterset_fields = ["role", "is_active"]
    search_fields = ["name", "email"]
    ordering = ["id"]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs

    @action(detail=False, methods=["post"])
    def create_student(self, request):
        serializer = StudentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        department = Department.objects.get(id=data["department_id"])
        academic_year = (
            AcademicYear.objects.get(id=data["academic_year_id"])
            if data.get("academic_year_id")
            else None
        )
        user = UserService.create_student(
            email=data["email"],
            name=data["name"],
            password=data["password"],
            roll_number=data["roll_number"],
            department=department,
            academic_year=academic_year,
            phone=data.get("phone", ""),
            created_by=request.user,
            request=request,
        )
        return Response(
            UserSummarySerializer(user).data, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["post"])
    def create_faculty(self, request):
        serializer = FacultyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        department = Department.objects.get(id=data["department_id"])
        user = UserService.create_faculty(
            email=data["email"],
            name=data["name"],
            password=data["password"],
            employee_id=data["employee_id"],
            department=department,
            designation=data.get("designation", ""),
            phone=data.get("phone", ""),
            created_by=request.user,
            request=request,
        )
        return Response(
            UserSummarySerializer(user).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        user = self.get_object()
        UserService.set_active(user, True, actor=request.user, request=request)
        return Response(UserSummarySerializer(user).data)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        UserService.set_active(user, False, actor=request.user, request=request)
        return Response(UserSummarySerializer(user).data)
