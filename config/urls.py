from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include
from django.urls import path
from django.views import defaults as default_views
from django.views.generic import TemplateView

from drf_spectacular.views import SpectacularAPIView
from drf_spectacular.views import SpectacularSwaggerView

urlpatterns = [
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path(
        "about/",
        TemplateView.as_view(template_name="pages/about.html"),
        name="about",
    ),
    # Django Admin
    path(settings.ADMIN_URL, admin.site.urls),
    # User management (allauth)
    path("users/", include("be_logbook.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
]

# API v1
urlpatterns += [
    path("api/v1/auth/", include("be_logbook.accounts.urls")),
    path("api/v1/users/", include("be_logbook.users.api.urls")),
    path("api/v1/academics/", include("be_logbook.academics.urls")),
    path("api/v1/groups/", include("be_logbook.groups.urls")),
    path("api/v1/projects/", include("be_logbook.projects.urls")),
    path("api/v1/workflow/", include("be_logbook.workflow.urls")),
    path("api/v1/submissions/", include("be_logbook.submissions.urls")),
    path("api/v1/documents/", include("be_logbook.documents.urls")),
    path("api/v1/reviews/", include("be_logbook.reviews.urls")),
    path("api/v1/rubrics/", include("be_logbook.assessments.urls")),
    path("api/v1/co-po/", include("be_logbook.co_po.urls")),
    path("api/v1/notifications/", include("be_logbook.notifications.urls")),
    path("api/v1/audit/", include("be_logbook.audit.urls")),
    path("api/v1/reports/", include("be_logbook.reports.urls")),
    path("api/v1/logbook/", include("be_logbook.logbook.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
]

if settings.DEBUG:
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
            *urlpatterns,
        ]
