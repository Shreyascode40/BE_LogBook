from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SubmissionsConfig(AppConfig):
    name = "be_logbook.submissions"
    verbose_name = _("Submissions")
