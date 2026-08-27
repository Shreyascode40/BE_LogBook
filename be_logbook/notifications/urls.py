from __future__ import annotations

from rest_framework.routers import DefaultRouter

from be_logbook.notifications.views import NotificationViewSet

router = DefaultRouter()
router.register("", NotificationViewSet, basename="notifications")

app_name = "notifications-api"
urlpatterns = router.urls
