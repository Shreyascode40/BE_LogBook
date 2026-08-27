from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LogbookConfig(AppConfig):
    name = "be_logbook.logbook"
    verbose_name = _("Logbook")
