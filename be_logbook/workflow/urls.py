from __future__ import annotations

from rest_framework.routers import DefaultRouter

from be_logbook.workflow.views import SectionViewSet
from be_logbook.workflow.views import StageDependencyViewSet
from be_logbook.workflow.views import StageViewSet

router = DefaultRouter()
router.register("stages", StageViewSet, basename="stages")
router.register("sections", SectionViewSet, basename="sections")
router.register(
    "stage-dependencies", StageDependencyViewSet, basename="stage-dependencies"
)

app_name = "workflow-api"
urlpatterns = router.urls
