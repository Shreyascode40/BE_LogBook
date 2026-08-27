from __future__ import annotations

from rest_framework.routers import DefaultRouter

from be_logbook.submissions.views import SubmissionViewSet

router = DefaultRouter()
router.register("", SubmissionViewSet, basename="submissions")

app_name = "submissions-api"
urlpatterns = router.urls
