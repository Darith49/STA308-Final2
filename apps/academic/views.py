"""
Academic app views:
- Admin: System dashboard, user management, departments/programs/courses CRUD, audit log.
- Department Head: Scoped department dashboard, live filter charts, paginated record browsing, CSV export.
- Student: Self-service portal with grades, attendance, GPA trend chart, profile editing.
- REST endpoints for Chart.js updates.
"""

import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.accounts.models import UserProfile, UserRole, AuditLog, log_audit_event
from apps.academic.models import Department, Program, Course, Student, Grade, Attendance
from apps.academic.scoping import role_required, scope_for, get_user_department
from apps.academic.forms import (
    AdminUserCreateForm,
    DepartmentForm,
    ProgramForm,
    CourseForm,
    StudentProfileEditForm,
)
from apps.uploads.models import Upload, UploadStatus
from apps.uploads.validators import sanitize_formula_injection


# ==============================================================================
# ADMIN ROLE VIEWS
# ==============================================================================

@login_required
@role_required(UserRole.ADMIN, UserRole.DATA_ANALYST)
def admin_system_dashboard_view(request):
    """Admin lands here: System-wide dashboard with KPIs, all charts, and activity log."""
    total_students = Student.objects.count()
    total_courses = Course.objects.count()
    total_departments = Department.objects.count()
    total_grades = Grade.objects.count()
    
    avg_score = Grade.objects.aggregate(avg=Avg("numerical_score"))["avg"] or 0.0
    pass_count = Grade.objects.filter(passed=True).count()
    overall_pass_rate = round((pass_count / total_grades * 100), 1) if total_grades > 0 else 0.0

    total_att = Attendance.objects.count()
    attended_att = Attendance.objects.filter(status__in=["Present", "Late"]).count()
    attendance_rate = round((attended_att / total_att * 100), 1) if total_att > 0 else 0.0

    # Department breakdown
    departments = Department.objects.annotate(
        student_count=Count("students", distinct=True),
        course_count=Count("courses", distinct=True),
    ).order_by("code")

    dept_stats = []
    for d in departments:
        d_grades = Grade.objects.filter(course__department=d)
        d_avg = d_grades.aggregate(avg=Avg("numerical_score"))["avg"] or 0.0
        d_pass = d_grades.filter(passed=True).count()
        d_total_g = d_grades.count()
        d_pass_rate = round((d_pass / d_total_g * 100), 1) if d_total_g > 0 else 0.0
        dept_stats.append({
            "dept": d,
            "students": d.student_count,
            "courses": d.course_count,
            "avg_score": round(d_avg, 1),
            "pass_rate": d_pass_rate,
        })

    recent_uploads = Upload.objects.all().order_by("-created_at")[:6]
    recent_audits = AuditLog.objects.all().order_by("-timestamp")[:8]

    return render(
        request,
        "academic/admin_dashboard.html",
        {
            "total_students": total_students,
            "total_courses": total_courses,
            "total_departments": total_departments,
            "total_grades": total_grades,
            "avg_score": round(avg_score, 1),
            "overall_pass_rate": overall_pass_rate,
            "attendance_rate": attendance_rate,
            "dept_stats": dept_stats,
            "recent_uploads": recent_uploads,
            "recent_audits": recent_audits,
        },
    )


@login_required
@role_required(UserRole.ADMIN, UserRole.DATA_ANALYST)
def admin_users_list_view(request):
    """User Management: Create, deactivate, reset password, assign role & department."""
    search_q = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "")
    dept_filter = request.GET.get("department", "")

    users = User.objects.select_related("profile").order_by("-date_joined")
    if search_q:
        users = users.filter(
            Q(username__icontains=search_q)
            | Q(first_name__icontains=search_q)
            | Q(last_name__icontains=search_q)
            | Q(email__icontains=search_q)
        )
    if role_filter:
        users = users.filter(profile__role=role_filter)
    if dept_filter:
        users = users.filter(profile__department__icontains=dept_filter)

    paginator = Paginator(users, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    departments = Department.objects.all()
    create_form = AdminUserCreateForm()

    return render(
        request,
        "academic/admin_users.html",
        {
            "page_obj": page_obj,
            "search_q": search_q,
            "role_filter": role_filter,
            "dept_filter": dept_filter,
            "roles": UserRole.choices,
            "departments": departments,
            "create_form": create_form,
        },
    )


@login_required
@role_required(UserRole.ADMIN, UserRole.DATA_ANALYST)
@require_POST
def admin_user_create_view(request):
    """Create a new user with assigned role and department."""
    form = AdminUserCreateForm(request.POST)
    if form.is_valid():
        username = form.cleaned_data["username"]
        email = form.cleaned_data["email"]
        first_name = form.cleaned_data.get("first_name", "")
        last_name = form.cleaned_data.get("last_name", "")
        password = form.cleaned_data["password"]
        role = form.cleaned_data["role"]
        dept_obj = form.cleaned_data.get("department")

        dept_str = dept_obj.name if dept_obj else "Department of Statistics & Data Science"

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.department = dept_str
        profile.save()

        # If student role, check if student record exists and link it
        if role == UserRole.STUDENT:
            student = Student.objects.filter(email__iexact=email).first() or Student.objects.filter(student_id__iexact=username).first()
            if student:
                student.user = user
                student.save(update_fields=["user"])

        log_audit_event(
            request.user,
            "USER_CREATE",
            target_model="User",
            target_id=str(user.id),
            details=f"Created user '{username}' with role '{role}' in '{dept_str}'",
            request=request,
        )
        messages.success(request, f"User '{username}' created successfully.")
    else:
        for errs in form.errors.values():
            for err in errs:
                messages.error(request, err)
    return redirect("academic:admin-users")


@login_required
@role_required(UserRole.ADMIN, UserRole.DATA_ANALYST)
@require_POST
def admin_user_toggle_active_view(request, user_id):
    """Deactivate or activate an existing user account."""
    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("academic:admin-users")

    target_user.is_active = not target_user.is_active
    target_user.save(update_fields=["is_active"])

    action = "USER_ACTIVATE" if target_user.is_active else "USER_DEACTIVATE"
    status_str = "activated" if target_user.is_active else "deactivated"
    log_audit_event(
        request.user,
        action,
        target_model="User",
        target_id=str(target_user.id),
        details=f"User '{target_user.username}' was {status_str}",
        request=request,
    )
    messages.success(request, f"User '{target_user.username}' {status_str}.")
    return redirect("academic:admin-users")


@login_required
@role_required(UserRole.ADMIN, UserRole.DATA_ANALYST)
@require_POST
def admin_user_reset_password_view(request, user_id):
    """Reset a user's password directly."""
    target_user = get_object_or_404(User, id=user_id)
    new_password = request.POST.get("new_password", "").strip()
    if len(new_password) < 6:
        messages.error(request, "Password must be at least 6 characters.")
        return redirect("academic:admin-users")

    target_user.set_password(new_password)
    target_user.save()

    log_audit_event(
        request.user,
        "PASSWORD_RESET",
        target_model="User",
        target_id=str(target_user.id),
        details=f"Admin reset password for user '{target_user.username}'",
        request=request,
    )
    messages.success(request, f"Password for '{target_user.username}' has been reset.")
    return redirect("academic:admin-users")


@login_required
@role_required(UserRole.ADMIN, UserRole.DATA_ANALYST)
def admin_departments_crud_view(request):
    """CRUD interface for Departments, Programs, and Courses."""
    departments = Department.objects.all().order_by("code")
    programs = Program.objects.select_related("department").order_by("department__code", "code")
    courses = Course.objects.select_related("department", "program").order_by("department__code", "code")

    dept_form = DepartmentForm()
    prog_form = ProgramForm()
    course_form = CourseForm()

    return render(
        request,
        "academic/admin_departments.html",
        {
            "departments": departments,
            "programs": programs,
            "courses": courses,
            "dept_form": dept_form,
            "prog_form": prog_form,
            "course_form": course_form,
        },
    )


@login_required
@role_required(UserRole.ADMIN, UserRole.DATA_ANALYST)
@require_POST
def admin_department_create_view(request):
    form = DepartmentForm(request.POST)
    if form.is_valid():
        dept = form.save()
        log_audit_event(
            request.user,
            "DEPT_CREATE",
            target_model="Department",
            target_id=str(dept.id),
            details=f"Created department {dept.code} - {dept.name}",
            request=request,
        )
        messages.success(request, f"Department '{dept.code}' created.")
    else:
        for errs in form.errors.values():
            for err in errs:
                messages.error(request, err)
    return redirect("academic:admin-departments")


@login_required
@role_required(UserRole.ADMIN, UserRole.DATA_ANALYST)
@require_POST
def admin_department_delete_view(request, dept_id):
    dept = get_object_or_404(Department, id=dept_id)
    code = dept.code
    dept.delete()
    log_audit_event(
        request.user,
        "DEPT_DELETE",
        target_model="Department",
        target_id=str(dept_id),
        details=f"Deleted department '{code}'",
        request=request,
    )
    messages.success(request, f"Department '{code}' and linked programs/courses removed.")
    return redirect("academic:admin-departments")


@login_required
@role_required(UserRole.ADMIN, UserRole.DATA_ANALYST)
@require_POST
def admin_program_create_view(request):
    form = ProgramForm(request.POST)
    if form.is_valid():
        prog = form.save()
        log_audit_event(
            request.user,
            "PROGRAM_CREATE",
            target_model="Program",
            target_id=str(prog.id),
            details=f"Created program {prog.code} in {prog.department.code}",
            request=request,
        )
        messages.success(request, f"Program '{prog.code}' created.")
    else:
        for errs in form.errors.values():
            for err in errs:
                messages.error(request, err)
    return redirect("academic:admin-departments")


@login_required
@role_required(UserRole.ADMIN, UserRole.DATA_ANALYST)
@require_POST
def admin_program_delete_view(request, prog_id):
    prog = get_object_or_404(Program, id=prog_id)
    code = prog.code
    prog.delete()
    log_audit_event(
        request.user,
        "PROGRAM_DELETE",
        target_model="Program",
        target_id=str(prog_id),
        details=f"Deleted program '{code}'",
        request=request,
    )
    messages.success(request, f"Program '{code}' removed.")
    return redirect("academic:admin-departments")


@login_required
@role_required(UserRole.ADMIN, UserRole.DATA_ANALYST)
@require_POST
def admin_course_create_view(request):
    form = CourseForm(request.POST)
    if form.is_valid():
        course = form.save()
        log_audit_event(
            request.user,
            "COURSE_CREATE",
            target_model="Course",
            target_id=str(course.id),
            details=f"Created course {course.code}: {course.title}",
            request=request,
        )
        messages.success(request, f"Course '{course.code}' created.")
    else:
        for errs in form.errors.values():
            for err in errs:
                messages.error(request, err)
    return redirect("academic:admin-departments")


@login_required
@role_required(UserRole.ADMIN, UserRole.DATA_ANALYST)
@require_POST
def admin_course_delete_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    code = course.code
    course.delete()
    log_audit_event(
        request.user,
        "COURSE_DELETE",
        target_model="Course",
        target_id=str(course_id),
        details=f"Deleted course '{code}'",
        request=request,
    )
    messages.success(request, f"Course '{code}' removed.")
    return redirect("academic:admin-departments")


@login_required
@role_required(UserRole.ADMIN, UserRole.DATA_ANALYST)
def admin_audit_log_view(request):
    """System-wide immutable audit trail viewer."""
    action_filter = request.GET.get("action", "")
    user_filter = request.GET.get("user", "")

    audits = AuditLog.objects.select_related("user").order_by("-timestamp")
    if action_filter:
        audits = audits.filter(action=action_filter)
    if user_filter:
        audits = audits.filter(user__username__icontains=user_filter)

    paginator = Paginator(audits, 30)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "academic/admin_audit_log.html",
        {
            "page_obj": page_obj,
            "action_filter": action_filter,
            "user_filter": user_filter,
            "actions": AuditLog.ACTION_CHOICES,
        },
    )


# ==============================================================================
# DEPARTMENT HEAD / LECTURER VIEWS (READ-ONLY, OWN DEPARTMENT)
# ==============================================================================

@login_required
@role_required(UserRole.DEPT_HEAD, UserRole.FACULTY, UserRole.ADMIN)
def dept_dashboard_view(request):
    """
    Department Head Dashboard.
    Strictly scoped to user's assigned department via scope_for(request.user).
    """
    dept = get_user_department(request.user)
    
    # If Admin, allow selecting department or default to first
    if request.user.profile.is_admin:
        dept_code = request.GET.get("dept_code")
        if dept_code:
            dept = Department.objects.filter(code__iexact=dept_code).first()
        if not dept:
            dept = Department.objects.first()

    if not dept:
        messages.error(request, "No department assigned to your account. Please contact an administrator.")
        return render(request, "403.html", {"message": "No department affiliation configured for this account."}, status=403)

    # Scoped queries
    dept_students = scope_for(request.user, Student).filter(department=dept) if not request.user.profile.is_admin else Student.objects.filter(department=dept)
    dept_courses = scope_for(request.user, Course).filter(department=dept) if not request.user.profile.is_admin else Course.objects.filter(department=dept)
    dept_grades = Grade.objects.filter(course__department=dept)
    dept_attendance = Attendance.objects.filter(course__department=dept)

    # Department KPIs
    total_students = dept_students.count()
    total_courses = dept_courses.count()
    total_grades = dept_grades.count()
    avg_score = dept_grades.aggregate(avg=Avg("numerical_score"))["avg"] or 0.0
    pass_count = dept_grades.filter(passed=True).count()
    pass_rate = round((pass_count / total_grades * 100), 1) if total_grades > 0 else 0.0

    total_att = dept_attendance.count()
    attended = dept_attendance.filter(status__in=["Present", "Late"]).count()
    attendance_rate = round((attended / total_att * 100), 1) if total_att > 0 else 0.0

    # Filter options
    semesters = sorted(list(dept_grades.values_list("semester", flat=True).distinct()))
    programs = dept.programs.all()
    courses_list = dept_courses.all()

    # Pass rate by course (initial data)
    course_stats = []
    for c in dept_courses[:10]:
        c_grades = dept_grades.filter(course=c)
        c_total = c_grades.count()
        c_pass = c_grades.filter(passed=True).count()
        rate = round((c_pass / c_total * 100), 1) if c_total > 0 else 0.0
        course_stats.append({
            "code": c.code,
            "title": c.title,
            "total": c_total,
            "pass_rate": rate,
        })

    all_departments = Department.objects.all() if request.user.profile.is_admin else None

    return render(
        request,
        "academic/dept_dashboard.html",
        {
            "department": dept,
            "total_students": total_students,
            "total_courses": total_courses,
            "avg_score": round(avg_score, 1),
            "pass_rate": pass_rate,
            "attendance_rate": attendance_rate,
            "semesters": semesters,
            "programs": programs,
            "courses_list": courses_list,
            "course_stats": course_stats,
            "all_departments": all_departments,
        },
    )


@login_required
@role_required(UserRole.DEPT_HEAD, UserRole.FACULTY, UserRole.ADMIN)
def dept_browse_records_view(request):
    """
    Browse student, course, and grade records with search and pagination.
    Strictly scoped to user's assigned department.
    """
    dept = get_user_department(request.user)
    if request.user.profile.is_admin:
        dept_code = request.GET.get("dept_code")
        if dept_code:
            dept = Department.objects.filter(code__iexact=dept_code).first()
        if not dept:
            dept = Department.objects.first()

    if not dept:
        return render(request, "403.html", {"message": "No department assigned to your account."}, status=403)

    tab = request.GET.get("tab", "students")
    search_q = request.GET.get("q", "").strip()

    if tab == "courses":
        qs = scope_for(request.user, Course).filter(department=dept) if not request.user.profile.is_admin else Course.objects.filter(department=dept)
        if search_q:
            qs = qs.filter(Q(code__icontains=search_q) | Q(title__icontains=search_q))
        paginator = Paginator(qs.order_by("code"), 20)

    elif tab == "grades":
        qs = Grade.objects.filter(course__department=dept).select_related("student", "course")
        if search_q:
            qs = qs.filter(Q(student__student_id__icontains=search_q) | Q(student__first_name__icontains=search_q) | Q(course__code__icontains=search_q))
        paginator = Paginator(qs.order_by("-semester", "course__code"), 25)

    elif tab == "attendance":
        qs = Attendance.objects.filter(course__department=dept).select_related("student", "course")
        if search_q:
            qs = qs.filter(Q(student__student_id__icontains=search_q) | Q(course__code__icontains=search_q))
        paginator = Paginator(qs.order_by("-date"), 25)

    else:  # students
        tab = "students"
        qs = scope_for(request.user, Student).filter(department=dept).select_related("program") if not request.user.profile.is_admin else Student.objects.filter(department=dept).select_related("program")
        if search_q:
            qs = qs.filter(
                Q(student_id__icontains=search_q)
                | Q(first_name__icontains=search_q)
                | Q(last_name__icontains=search_q)
                | Q(email__icontains=search_q)
            )
        paginator = Paginator(qs.order_by("student_id"), 20)

    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "academic/dept_browse.html",
        {
            "department": dept,
            "tab": tab,
            "search_q": search_q,
            "page_obj": page_obj,
        },
    )


@login_required
@role_required(UserRole.DEPT_HEAD, UserRole.FACULTY, UserRole.ADMIN)
def dept_export_csv_view(request, record_type):
    """
    Exports filtered table to CSV, with strict server-side scoping
    and formula injection sanitization on every cell.
    """
    dept = get_user_department(request.user)
    if request.user.profile.is_admin:
        dept_code = request.GET.get("dept_code")
        if dept_code:
            dept = Department.objects.filter(code__iexact=dept_code).first()
        if not dept:
            dept = Department.objects.first()

    if not dept:
        return render(request, "403.html", {"message": "No department assigned to your account."}, status=403)

    response = HttpResponse(content_type="text/csv")
    timestamp_str = timezone.now().strftime("%Y%m%d_%H%M")
    response["Content-Disposition"] = f'attachment; filename="{dept.code}_{record_type}_{timestamp_str}.csv"'

    writer = csv.writer(response)

    if record_type == "students":
        students = Student.objects.filter(department=dept).select_related("program").order_by("student_id")
        writer.writerow(["Student ID", "First Name", "Last Name", "Email", "Department", "Program", "Cohort", "Status", "Current GPA"])
        for s in students:
            row = [
                s.student_id,
                s.first_name,
                s.last_name,
                s.email,
                dept.code,
                s.program.code if s.program else "",
                s.cohort,
                s.status,
                s.current_gpa,
            ]
            writer.writerow([sanitize_formula_injection(val) for val in row])

    elif record_type == "courses":
        courses = Course.objects.filter(department=dept).select_related("program").order_by("code")
        writer.writerow(["Course Code", "Title", "Department", "Program", "Credits", "Semester"])
        for c in courses:
            row = [
                c.code,
                c.title,
                dept.code,
                c.program.code if c.program else "",
                c.credits,
                c.semester,
            ]
            writer.writerow([sanitize_formula_injection(val) for val in row])

    elif record_type == "grades":
        grades = Grade.objects.filter(course__department=dept).select_related("student", "course").order_by("-semester", "course__code")
        writer.writerow(["Student ID", "Student Name", "Course Code", "Course Title", "Semester", "Numerical Score", "Letter Grade", "GPA Points", "Passed"])
        for g in grades:
            row = [
                g.student.student_id,
                g.student.full_name,
                g.course.code,
                g.course.title,
                g.semester,
                g.numerical_score,
                g.letter_grade,
                g.gpa_points,
                "Yes" if g.passed else "No",
            ]
            writer.writerow([sanitize_formula_injection(val) for val in row])

    elif record_type == "attendance":
        records = Attendance.objects.filter(course__department=dept).select_related("student", "course").order_by("-date")
        writer.writerow(["Student ID", "Student Name", "Course Code", "Date", "Status", "Topic"])
        for a in records:
            row = [
                a.student.student_id,
                a.student.full_name,
                a.course.code,
                a.date.isoformat(),
                a.status,
                a.session_topic,
            ]
            writer.writerow([sanitize_formula_injection(val) for val in row])

    else:
        raise Http404("Invalid export record type.")

    # Audit log entry
    log_audit_event(
        request.user,
        "EXPORT_CSV",
        target_model=record_type.capitalize(),
        target_id=dept.code,
        details=f"Exported {record_type} CSV for department {dept.code}",
        request=request,
    )

    return response


# ==============================================================================
# STUDENT VIEWS (STRETCH GOAL)
# ==============================================================================

@login_required
def student_portal_view(request):
    """
    Student Self-Service Portal.
    Strictly displays only the logged-in student's personal records.
    """
    user = request.user
    # Find student profile
    student = Student.objects.filter(user=user).first()
    if not student:
        # Match by username as student_id or email
        student = Student.objects.filter(Q(student_id__iexact=user.username) | Q(email__iexact=user.email)).first()
        if student and not student.user:
            student.user = user
            student.save(update_fields=["user"])

    if not student:
        messages.info(request, "No student profile is currently linked to your login. Contact your department administrator.")
        return render(request, "academic/student_not_linked.html", {"user": user})

    # Scoped queries for this student only
    grades = student.grades.select_related("course").order_by("-semester", "course__code")
    attendance = student.attendance_records.select_related("course").order_by("-date")

    # GPA Calculation
    current_gpa = student.current_gpa
    attendance_rate = student.attendance_rate
    total_credits = sum(g.course.credits for g in grades if g.passed)

    # GPA trend by semester
    semester_gpas = {}
    for g in grades:
        sem = g.semester
        if sem not in semester_gpas:
            semester_gpas[sem] = []
        semester_gpas[sem].append(g.gpa_points)

    gpa_trend = []
    for sem, pts in semester_gpas.items():
        gpa_trend.append({
            "semester": sem,
            "gpa": round(sum(pts) / len(pts), 2),
        })

    return render(
        request,
        "academic/student_portal.html",
        {
            "student": student,
            "grades": grades,
            "attendance": attendance[:20],
            "total_attendance_records": attendance.count(),
            "current_gpa": current_gpa,
            "attendance_rate": attendance_rate,
            "total_credits": total_credits,
            "gpa_trend": gpa_trend,
        },
    )


@login_required
def student_profile_edit_view(request):
    """Student edits their profile details and/or changes password."""
    user = request.user
    student = Student.objects.filter(user=user).first()

    if request.method == "POST":
        form = StudentProfileEditForm(request.POST)
        if form.is_valid():
            user.first_name = form.cleaned_data["first_name"]
            user.last_name = form.cleaned_data["last_name"]
            user.email = form.cleaned_data["email"]

            new_pw = form.cleaned_data.get("new_password")
            if new_pw and len(new_pw) >= 6:
                user.set_password(new_pw)
                messages.success(request, "Password updated successfully. Please log in again if required.")

            user.save()

            if hasattr(user, "profile"):
                user.profile.phone = form.cleaned_data.get("phone", "")
                user.profile.save()

            if student:
                student.first_name = user.first_name
                student.last_name = user.last_name
                student.email = user.email
                student.save()

            messages.success(request, "Your profile details have been updated.")
            return redirect("academic:student-portal")
    else:
        initial = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": getattr(getattr(user, "profile", None), "phone", ""),
        }
        form = StudentProfileEditForm(initial=initial)

    return render(request, "academic/student_profile_edit.html", {"form": form, "student": student})


# ==============================================================================
# AJAX / REST CHART DATA APIS
# ==============================================================================

@login_required
def api_dept_chart_data(request):
    """
    AJAX endpoint for department dashboard interactive Chart.js charts.
    Supports filtering by semester, program, course.
    """
    dept = get_user_department(request.user)
    if request.user.profile.is_admin:
        dept_code = request.GET.get("dept_code")
        if dept_code:
            dept = Department.objects.filter(code__iexact=dept_code).first()
        if not dept:
            dept = Department.objects.first()

    if not dept:
        return JsonResponse({"error": "Unauthorized or no department"}, status=403)

    semester = request.GET.get("semester")
    program_id = request.GET.get("program")
    course_code = request.GET.get("course")

    grades_qs = Grade.objects.filter(course__department=dept)
    att_qs = Attendance.objects.filter(course__department=dept)

    if semester and semester != "all":
        grades_qs = grades_qs.filter(semester=semester)
    if program_id and program_id != "all":
        grades_qs = grades_qs.filter(course__program_id=program_id)
        att_qs = att_qs.filter(course__program_id=program_id)
    if course_code and course_code != "all":
        grades_qs = grades_qs.filter(course__code=course_code)
        att_qs = att_qs.filter(course__code=course_code)

    # 1. Score Distribution (Histogram Bins)
    scores = list(grades_qs.values_list("numerical_score", flat=True))
    bins = {"<60 (F)": 0, "60-69 (D)": 0, "70-79 (C)": 0, "80-89 (B)": 0, "90-100 (A)": 0}
    for s in scores:
        if s < 60:
            bins["<60 (F)"] += 1
        elif s < 70:
            bins["60-69 (D)"] += 1
        elif s < 80:
            bins["70-79 (C)"] += 1
        elif s < 90:
            bins["80-89 (B)"] += 1
        else:
            bins["90-100 (A)"] += 1

    # 2. Pass Rate by Course
    courses = Course.objects.filter(department=dept)
    if course_code and course_code != "all":
        courses = courses.filter(code=course_code)

    course_labels = []
    course_pass_rates = []
    for c in courses[:12]:
        c_grades = grades_qs.filter(course=c)
        c_total = c_grades.count()
        c_pass = c_grades.filter(passed=True).count()
        rate = round((c_pass / c_total * 100), 1) if c_total > 0 else 0.0
        course_labels.append(c.code)
        course_pass_rates.append(rate)

    # 3. Attendance Status Breakdown
    att_counts = {
        "Present": att_qs.filter(status="Present").count(),
        "Absent": att_qs.filter(status="Absent").count(),
        "Late": att_qs.filter(status="Late").count(),
        "Excused": att_qs.filter(status="Excused").count(),
    }

    # Summary KPIs
    total_students = grades_qs.values("student").distinct().count()
    avg_score = grades_qs.aggregate(avg=Avg("numerical_score"))["avg"] or 0.0
    total_g = grades_qs.count()
    pass_cnt = grades_qs.filter(passed=True).count()
    pass_rate = round((pass_cnt / total_g * 100), 1) if total_g > 0 else 0.0

    return JsonResponse({
        "score_distribution": {
            "labels": list(bins.keys()),
            "values": list(bins.values()),
        },
        "pass_rates": {
            "labels": course_labels,
            "values": course_pass_rates,
        },
        "attendance": {
            "labels": list(att_counts.keys()),
            "values": list(att_counts.values()),
        },
        "kpis": {
            "total_students": total_students,
            "avg_score": round(avg_score, 1),
            "pass_rate": pass_rate,
            "total_grades": total_g,
        }
    })
