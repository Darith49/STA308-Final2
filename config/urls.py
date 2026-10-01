from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from academics.views import (
    DashboardView, StudentListView, StudentExportCsvView,
    CourseListView, EnrollmentListView, EnrollmentExportCsvView,
    AttendanceListView
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', DashboardView.as_view(), name='dashboard'),
    path('dashboard/', DashboardView.as_view(), name='dashboard_alt'),
    path('students/', StudentListView.as_view(), name='students_list'),
    path('students/export/csv/', StudentExportCsvView.as_view(), name='students_export_csv'),
    path('courses/', CourseListView.as_view(), name='courses_list'),
    path('grades/', EnrollmentListView.as_view(), name='grades_list'),
    path('grades/export/csv/', EnrollmentExportCsvView.as_view(), name='grades_export_csv'),
    path('attendance/', AttendanceListView.as_view(), name='attendance_list'),
    path('accounts/', include('accounts.urls')),
    path('uploads/', include('uploads.urls')),
    path('', include('analytics.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
