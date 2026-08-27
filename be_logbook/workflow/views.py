from __future__ import annotations

from rest_framework.viewsets import ModelViewSet

from be_logbook.utils.permissions import IsHOD
from be_logbook.utils.permissions import IsHODOrFaculty
from be_logbook.workflow.models import Section
from be_logbook.workflow.models import Stage
from be_logbook.workflow.models import StageDependency
from be_logbook.workflow.serializers import SectionSerializer
from be_logbook.workflow.serializers import StageDependencySerializer
from be_logbook.workflow.serializers import StageSerializer


class StageViewSet(ModelViewSet):
    queryset = Stage.objects.all().order_by("display_order")
    serializer_class = StageSerializer
    permission_classes = [IsHOD]
    filterset_fields = ["is_active", "required"]
    ordering = ["display_order"]


class SectionViewSet(ModelViewSet):
    queryset = Section.objects.all().select_related("stage")
    serializer_class = SectionSerializer
    permission_classes = [IsHOD]
    filterset_fields = ["stage", "section_type", "is_active"]


class StageDependencyViewSet(ModelViewSet):
    queryset = StageDependency.objects.all().select_related("stage", "depends_on")
    serializer_class = StageDependencySerializer
    permission_classes = [IsHOD]
