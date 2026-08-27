from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AccountsConfig(AppConfig):
    name = "be_logbook.accounts"
    verbose_name = _("Accounts")
