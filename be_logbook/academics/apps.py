from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AcademicsConfig(AppConfig):
    name = "be_logbook.academics"
    verbose_name = _("Academics")
