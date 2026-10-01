from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('api/kpis/', views.KpiSummaryApiView.as_view(), name='api_kpis'),
    path('api/charts/students-by-department/', views.StudentsByDepartmentChartApiView.as_view(), name='api_chart_students_dept'),
    path('api/charts/year-distribution/', views.YearDistributionChartApiView.as_view(), name='api_chart_year_dist'),
    path('api/charts/enrollment-trend/', views.EnrollmentTrendChartApiView.as_view(), name='api_chart_enrollment_trend'),
    path('api/charts/grade-distribution/', views.GradeDistributionChartApiView.as_view(), name='api_chart_grade_dist'),
    path('api/charts/pass-rate-by-course/', views.PassRateByCourseChartApiView.as_view(), name='api_chart_pass_rate'),
    path('api/charts/attendance-trend/', views.AttendanceTrendChartApiView.as_view(), name='api_chart_attendance_trend'),
]
