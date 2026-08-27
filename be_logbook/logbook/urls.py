from __future__ import annotations

from django.urls import path

from be_logbook.logbook.views import LogBookDownloadView
from be_logbook.logbook.views import LogBookGenerateView

app_name = "logbook-api"
urlpatterns = [
    path("generate/<int:project_id>/", LogBookGenerateView.as_view(), name="generate"),
    path("<int:pk>/download/", LogBookDownloadView.as_view(), name="download"),
]
