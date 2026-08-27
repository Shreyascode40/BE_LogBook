from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class GroupsConfig(AppConfig):
    name = "be_logbook.groups"
    verbose_name = _("Groups")
