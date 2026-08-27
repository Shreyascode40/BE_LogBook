from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from be_logbook.co_po.models import CO
from be_logbook.co_po.models import PO
from be_logbook.co_po.serializers import COSerializer
from be_logbook.co_po.serializers import POSerializer
from be_logbook.co_po.services import COPOService
from be_logbook.groups.models import ProjectGroup
from be_logbook.utils.access import can_access_group
from be_logbook.utils.access import is_hod
from be_logbook.utils.permissions import IsHODOrFaculty


class COViewSet(ModelViewSet):
    queryset = CO.objects.all()
    serializer_class = COSerializer
    permission_classes = [IsHODOrFaculty]
    ordering = ["code"]


class POViewSet(ModelViewSet):
    queryset = PO.objects.all()
    serializer_class = POSerializer
    permission_classes = [IsHODOrFaculty]
    ordering = ["code"]


class GroupCOPOView(APIView):
    def get(self, request, pk):
        group = get_object_or_404(ProjectGroup, id=pk)
        if not (is_hod(request.user) or can_access_group(request.user, group)):
            return Response(
                {"success": False, "message": "Forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        data = COPOService.compute_for_group(group)
        return Response({"success": True, "data": data})
