from __future__ import annotations

from django.urls import path

from be_logbook.accounts.views import LoginView
from be_logbook.accounts.views import LogoutView
from be_logbook.accounts.views import MeView
from be_logbook.accounts.views import RefreshView

app_name = "accounts"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
