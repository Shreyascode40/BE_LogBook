from __future__ import annotations

from rest_framework.routers import DefaultRouter

from be_logbook.audit.views import AuditLogViewSet

router = DefaultRouter()
router.register("", AuditLogViewSet, basename="audit")

app_name = "audit-api"
urlpatterns = router.urls
