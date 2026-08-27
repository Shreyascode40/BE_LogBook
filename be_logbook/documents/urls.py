from __future__ import annotations

from rest_framework.routers import DefaultRouter

from be_logbook.documents.views import DocumentViewSet

router = DefaultRouter()
router.register("", DocumentViewSet, basename="documents")

app_name = "documents-api"
urlpatterns = router.urls
