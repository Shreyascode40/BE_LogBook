from __future__ import annotations

from rest_framework import serializers

from be_logbook.co_po.models import CO
from be_logbook.co_po.models import PO


class COSerializer(serializers.ModelSerializer):
    class Meta:
        model = CO
        fields = ["id", "code", "description", "program"]


class POSerializer(serializers.ModelSerializer):
    class Meta:
        model = PO
        fields = ["id", "code", "description"]
