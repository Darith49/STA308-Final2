from django.urls import path
from . import views

app_name = 'academics'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('students/', views.StudentListView.as_view(), name='students_list'),
    path('students/export/csv/', views.StudentExportCsvView.as_view(), name='students_export_csv'),
    path('courses/', views.CourseListView.as_view(), name='courses_list'),
    path('grades/', views.EnrollmentListView.as_view(), name='grades_list'),
    path('grades/export/csv/', views.EnrollmentExportCsvView.as_view(), name='grades_export_csv'),
    path('attendance/', views.AttendanceListView.as_view(), name='attendance_list'),
]
