"""
Root URL configuration for University Data Portal.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

def home_redirect(request):
    if request.user.is_authenticated:
        return redirect("uploads:list")
    return redirect("accounts:login")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home_redirect, name="home"),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("uploads/", include("apps.uploads.urls", namespace="uploads")),
    path("", include("apps.dashboards.urls", namespace="dashboards")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
