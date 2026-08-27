from __future__ import annotations

from django.contrib import admin

from be_logbook.submissions.models import Approval
from be_logbook.submissions.models import ChangeRequest
from be_logbook.submissions.models import FacultyRemark
from be_logbook.submissions.models import StudentActivity
from be_logbook.submissions.models import Submission
from be_logbook.submissions.models import SubmissionVersion


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ["group", "stage", "section", "status", "version_number", "submitted_by"]
    list_filter = ["status", "stage"]
    search_fields = ["group__group_number"]


admin.site.register(SubmissionVersion)
admin.site.register(FacultyRemark)
admin.site.register(Approval)
admin.site.register(ChangeRequest)
admin.site.register(StudentActivity)
