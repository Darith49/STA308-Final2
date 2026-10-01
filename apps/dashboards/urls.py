from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.dashboards import views

app_name = "dashboards"

router = DefaultRouter()
router.register(r"dashboards", views.DashboardConfigViewSet, basename="dashboard-config")

urlpatterns = [
    # Template Views
    path("dashboard/", views.latest_dashboard_redirect, name="latest-dashboard"),
    path("uploads/<uuid:upload_id>/dashboard/", views.dashboard_view, name="view"),

    # DRF API Endpoints
    path("api/uploads/<uuid:upload_id>/status/", views.UploadStatusAPIView.as_view(), name="api-status"),
    path("api/uploads/<uuid:upload_id>/report/", views.UploadReportAPIView.as_view(), name="api-report"),
    path("api/uploads/<uuid:upload_id>/columns/", views.UploadColumnsAPIView.as_view(), name="api-columns"),
    path("api/uploads/<uuid:upload_id>/chart-data/", views.ChartDataAPIView.as_view(), name="api-chart-data"),
    path("api/", include(router.urls)),
]
