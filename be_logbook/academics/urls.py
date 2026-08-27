from __future__ import annotations

from rest_framework.routers import DefaultRouter

from be_logbook.academics.views import AcademicYearViewSet
from be_logbook.academics.views import DepartmentViewSet
from be_logbook.academics.views import TermViewSet

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="departments")
router.register("academic-years", AcademicYearViewSet, basename="academic-years")
router.register("terms", TermViewSet, basename="terms")

app_name = "academics-api"
urlpatterns = router.urls
