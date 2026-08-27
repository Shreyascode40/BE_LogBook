from __future__ import annotations

from rest_framework.routers import SimpleRouter

from be_logbook.reports.views import ReportViewSet

router = SimpleRouter()
router.register("", ReportViewSet, basename="reports")

app_name = "reports-api"
urlpatterns = router.urls
