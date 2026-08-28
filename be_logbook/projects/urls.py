from __future__ import annotations

from django.urls import path

from rest_framework.routers import DefaultRouter

from be_logbook.logbook.views import LogBookGenerateView
from be_logbook.logbook.views import LogBookRetrieveView
from be_logbook.projects.views import CompetitionDetailViewSet
from be_logbook.projects.views import FinalSubmissionInfoViewSet
from be_logbook.projects.views import ProjectScheduleViewSet
from be_logbook.projects.views import ProjectViewSet
from be_logbook.projects.views import PublicationDetailViewSet
from be_logbook.projects.views import TermRecordViewSet
from be_logbook.projects.views import TopicFinalizationViewSet

router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="projects")
router.register("schedules", ProjectScheduleViewSet, basename="schedules")
router.register(
    "topic-finalization", TopicFinalizationViewSet, basename="topic-finalization"
)
router.register(
    "final-submission", FinalSubmissionInfoViewSet, basename="final-submission"
)
router.register("competitions", CompetitionDetailViewSet, basename="competitions")
router.register("publications", PublicationDetailViewSet, basename="publications")
router.register("term-records", TermRecordViewSet, basename="term-records")

app_name = "projects-api"
urlpatterns = [
    path(
        "<int:project_id>/logbook/generate/",
        LogBookGenerateView.as_view(),
        name="logbook-generate",
    ),
    path(
        "<int:project_id>/logbook/",
        LogBookRetrieveView.as_view(),
        name="logbook-latest",
    ),
    *router.urls,
]
