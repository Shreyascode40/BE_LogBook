from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProjectsConfig(AppConfig):
    name = "be_logbook.projects"
    verbose_name = _("Projects")
