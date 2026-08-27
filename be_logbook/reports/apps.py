from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ReportsConfig(AppConfig):
    name = "be_logbook.reports"
    verbose_name = _("Reports")
