from __future__ import annotations

from rest_framework.viewsets import ModelViewSet

from be_logbook.academics.models import AcademicYear
from be_logbook.academics.models import Department
from be_logbook.academics.models import Term
from be_logbook.academics.serializers import AcademicYearSerializer
from be_logbook.academics.serializers import DepartmentSerializer
from be_logbook.academics.serializers import TermSerializer
from be_logbook.utils.permissions import IsHOD


class DepartmentViewSet(ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsHOD]
    search_fields = ["code", "name"]


class AcademicYearViewSet(ModelViewSet):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    permission_classes = [IsHOD]
    search_fields = ["name"]


class TermViewSet(ModelViewSet):
    queryset = Term.objects.all()
    serializer_class = TermSerializer
    permission_classes = [IsHOD]
    filterset_fields = ["academic_year"]
