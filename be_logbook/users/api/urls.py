from __future__ import annotations

from rest_framework.routers import DefaultRouter

from be_logbook.users.api.views import UserManagementViewSet

router = DefaultRouter()
router.register("", UserManagementViewSet, basename="users")

app_name = "users-api"
urlpatterns = router.urls
