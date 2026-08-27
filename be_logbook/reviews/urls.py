from __future__ import annotations

from rest_framework.routers import DefaultRouter

from be_logbook.reviews.views import ReviewAssignmentViewSet
from be_logbook.reviews.views import ReviewViewSet

router = DefaultRouter()
router.register("assignments", ReviewAssignmentViewSet, basename="review-assignments")
router.register("", ReviewViewSet, basename="reviews")

app_name = "reviews-api"
urlpatterns = router.urls
