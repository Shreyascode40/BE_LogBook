from __future__ import annotations

from rest_framework.routers import DefaultRouter
from rest_framework.urls import path

from be_logbook.co_po.views import COViewSet
from be_logbook.co_po.views import GroupCOPOView
from be_logbook.co_po.views import POViewSet

router = DefaultRouter()
router.register("cos", COViewSet, basename="cos")
router.register("pos", POViewSet, basename="pos")

app_name = "co-po-api"
urlpatterns = [
    path("group/<int:pk>/", GroupCOPOView.as_view(), name="group-attainment"),
] + router.urls
