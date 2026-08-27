from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from be_logbook.assessments.models import Rubric
from be_logbook.assessments.models import RubricCriterion
from be_logbook.assessments.serializers import RubricCriterionCreateSerializer
from be_logbook.assessments.serializers import RubricCriterionSerializer
from be_logbook.assessments.serializers import RubricSerializer
from be_logbook.utils.permissions import IsHOD


class RubricViewSet(ModelViewSet):
    queryset = Rubric.objects.all().prefetch_related("criteria")
    serializer_class = RubricSerializer
    permission_classes = [IsHOD]
    filterset_fields = ["is_active", "academic_year"]

    @action(detail=True, methods=["post"])
    def add_criterion(self, request, pk=None):
        rubric = self.get_object()
        serializer = RubricCriterionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        order = RubricCriterion.objects.filter(rubric=rubric).count() + 1
        criterion = RubricCriterion.objects.create(rubric=rubric, order=order, **data)
        return Response(
            RubricCriterionSerializer(criterion).data, status=status.HTTP_201_CREATED
        )
