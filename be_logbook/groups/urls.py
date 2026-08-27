from __future__ import annotations

from rest_framework.routers import DefaultRouter

from be_logbook.groups.views import ProjectGroupViewSet

router = DefaultRouter()
router.register("", ProjectGroupViewSet, basename="groups")

app_name = "groups-api"
urlpatterns = router.urls
