from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class NotificationsConfig(AppConfig):
    name = "be_logbook.notifications"
    verbose_name = _("Notifications")
