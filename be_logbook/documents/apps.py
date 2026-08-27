from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DocumentsConfig(AppConfig):
    name = "be_logbook.documents"
    verbose_name = _("Documents")
