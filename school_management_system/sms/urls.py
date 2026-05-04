from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from core import views as core_views
from core.custom_login import SchoolLoginView
from core import error_handlers
from core.api.auth import (
    ChangePasswordView,
    LoginView,
    LogoutView as APILogoutView,
    MeView,
    TokenRefreshView,
)

# Set custom error handlers
handler403 = error_handlers.handler403

# ── REST API v1 ────────────────────────────────────────────────────────────────
api_auth_patterns = [
    path("login/",           LoginView.as_view(),          name="api-login"),
    path("logout/",          APILogoutView.as_view(),       name="api-logout"),
    path("refresh/",         TokenRefreshView.as_view(),    name="api-token-refresh"),
    path("change-password/", ChangePasswordView.as_view(),  name="api-change-password"),
    path("me/",              MeView.as_view(),              name="api-me"),
]

urlpatterns = [
    path("admin/", admin.site.urls),

    # ── REST API v1
    path("api/v1/auth/",        include((api_auth_patterns, "auth"))),
    path("api/v1/",             include("tenants.urls")),
    path("api/v1/students/",    include("students.api_urls")),
    path("api/v1/academics/",   include("academics.api_urls")),
    path("api/v1/fees/",        include("fees.api_urls")),
    path("api/v1/attendance/",  include("attendance.api_urls")),
    path("api/v1/timetable/",   include("timetable.api_urls")),
    path("api/v1/elearning/",   include("elearning.api_urls")),
    path("api/v1/core/",        include("core.api_urls")),

    # ── Template-based views (unchanged — keep existing UI working)
    path("", include("core.urls")),
    path("students/",   include("students.urls")),
    path("academics/",  include("academics.urls")),
    path("timetable/",  include("timetable.urls")),
    path("fees/",       include("fees.urls")),
    path("elearning/",  include("elearning.urls")),

    # auth (template)
    path("login/",            SchoolLoginView.as_view(), name="login"),
    path("logout/",           core_views.logout_view,   name="logout"),
    path("accounts/profile/", RedirectView.as_view(url="/")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
