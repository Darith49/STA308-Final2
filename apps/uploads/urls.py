from django.urls import path
from apps.uploads import views

app_name = "uploads"

urlpatterns = [
    path("", views.upload_list_view, name="list"),
    path("new/", views.upload_create_view, name="create"),
    path("<uuid:upload_id>/processing/", views.upload_processing_view, name="processing"),
    path("<uuid:upload_id>/report/", views.upload_report_view, name="report"),
    path("<uuid:upload_id>/download/", views.upload_download_view, name="download"),
    path("<uuid:upload_id>/rerun/", views.upload_rerun_view, name="rerun"),
    path("<uuid:upload_id>/delete/", views.upload_delete_view, name="delete"),
]
