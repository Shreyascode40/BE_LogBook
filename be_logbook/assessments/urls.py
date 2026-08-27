from __future__ import annotations

from rest_framework.routers import DefaultRouter

from be_logbook.assessments.views import RubricViewSet

router = DefaultRouter()
router.register("rubrics", RubricViewSet, basename="rubrics")

app_name = "assessments-api"
urlpatterns = router.urls
