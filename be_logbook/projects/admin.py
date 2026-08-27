from __future__ import annotations

from django.contrib import admin

from be_logbook.projects.models import CompetitionDetail
from be_logbook.projects.models import FinalSubmissionInfo
from be_logbook.projects.models import Project
from be_logbook.projects.models import ProjectSchedule
from be_logbook.projects.models import PublicationDetail
from be_logbook.projects.models import TermRecord
from be_logbook.projects.models import TopicFinalization


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["title", "group", "guide", "area"]
    search_fields = ["title", "area"]
    list_filter = ["area"]


for model in (ProjectSchedule, TopicFinalization, FinalSubmissionInfo, CompetitionDetail, PublicationDetail, TermRecord):
    admin.site.register(model)
