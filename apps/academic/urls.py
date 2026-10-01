from django.urls import path
from apps.academic import views

app_name = "academic"

urlpatterns = [
    # Admin System Dashboard & User Management
    path("admin/overview/", views.admin_system_dashboard_view, name="admin-dashboard"),
    path("admin/users/", views.admin_users_list_view, name="admin-users"),
    path("admin/users/create/", views.admin_user_create_view, name="admin-user-create"),
    path("admin/users/<int:user_id>/toggle-active/", views.admin_user_toggle_active_view, name="admin-user-toggle"),
    path("admin/users/<int:user_id>/reset-password/", views.admin_user_reset_password_view, name="admin-user-reset-pw"),
    
    # Admin Departments, Programs, Courses CRUD
    path("admin/departments/", views.admin_departments_crud_view, name="admin-departments"),
    path("admin/departments/create/", views.admin_department_create_view, name="admin-dept-create"),
    path("admin/departments/<int:dept_id>/delete/", views.admin_department_delete_view, name="admin-dept-delete"),
    path("admin/programs/create/", views.admin_program_create_view, name="admin-program-create"),
    path("admin/programs/<int:prog_id>/delete/", views.admin_program_delete_view, name="admin-program-delete"),
    path("admin/courses/create/", views.admin_course_create_view, name="admin-course-create"),
    path("admin/courses/<int:course_id>/delete/", views.admin_course_delete_view, name="admin-course-delete"),
    
    # Admin Audit Log
    path("admin/audit-log/", views.admin_audit_log_view, name="admin-audit-log"),

    # Department Head Dashboard & Scoped Browsing
    path("department/dashboard/", views.dept_dashboard_view, name="dept-dashboard"),
    path("department/browse/", views.dept_browse_records_view, name="dept-browse"),
    path("department/export/<str:record_type>/", views.dept_export_csv_view, name="dept-export"),

    # Student Self-Service Portal (Stretch Goal)
    path("student/portal/", views.student_portal_view, name="student-portal"),
    path("student/profile/edit/", views.student_profile_edit_view, name="student-profile-edit"),

    # Dynamic Chart.js APIs
    path("api/dept-chart-data/", views.api_dept_chart_data, name="api-dept-chart-data"),
]
