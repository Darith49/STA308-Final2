"""
Root URL configuration for University Data Portal.
Dispatches authenticated users dynamically to their role-specific portals.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from apps.accounts.models import UserRole


def role_home_redirect(request):
    """
    Role-based entry point dispatch:
    - Admin -> System Dashboard
    - Registrar -> Uploads Portal & Templates
    - Department Head -> Department Dashboard
    - Student -> Student Self-Service Portal
    """
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    profile = getattr(request.user, "profile", None)
    if not profile or profile.is_admin:
        return redirect("academic:admin-dashboard")
    elif profile.is_registrar:
        return redirect("uploads:list")
    elif profile.is_dept_head:
        return redirect("academic:dept-dashboard")
    elif profile.is_student:
        return redirect("academic:student-portal")

    return redirect("uploads:list")


urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", role_home_redirect, name="home"),
    path("academic/", include("apps.academic.urls", namespace="academic")),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("uploads/", include("apps.uploads.urls", namespace="uploads")),
    path("", include("apps.dashboards.urls", namespace="dashboards")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
