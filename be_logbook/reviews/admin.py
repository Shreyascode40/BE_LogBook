from __future__ import annotations

from django.contrib import admin

from be_logbook.reviews.models import Review
from be_logbook.reviews.models import ReviewAssignment
from be_logbook.reviews.models import ReviewMark
from be_logbook.reviews.models import ReviewMarkCorrection


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["id", "group", "reviewer", "stage", "status", "total_obtained", "total_max"]
    list_filter = ["status", "stage"]


admin.site.register(ReviewAssignment)
admin.site.register(ReviewMark)
admin.site.register(ReviewMarkCorrection)
