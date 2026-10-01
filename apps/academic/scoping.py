"""
Security and Role-based Data Scoping utilities.
Enforces request lifecycle:
Request -> logged in? -> role allowed for page? -> data scoped to role (scope_for) -> response.
"""

from functools import wraps
from django.shortcuts import render, redirect
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from apps.accounts.models import UserRole


def get_user_department(user):
    """Retrieve the Department instance corresponding to the user's profile."""
    from apps.academic.models import Department
    if not hasattr(user, "profile"):
        return None
    dept_str = (user.profile.department or "").strip()
    if not dept_str:
        return None
    # Match by code (e.g. 'STAT') or name (e.g. 'Department of Statistics')
    dept = Department.objects.filter(code__iexact=dept_str).first()
    if not dept:
        dept = Department.objects.filter(name__icontains=dept_str).first()
    return dept


def user_has_role(user, *allowed_roles):
    """Check if the user is authenticated and belongs to one of the specified roles."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not hasattr(user, "profile"):
        return False
    
    user_role = user.profile.role
    
    # Normalize aliases:
    # DATA_ANALYST -> treated as admin/analyst
    # FACULTY -> treated as dept_head
    for role in allowed_roles:
        if user_role == role:
            return True
        if role == UserRole.ADMIN and (user_role in ["admin", "analyst"] or user.is_staff):
            return True
        if role == UserRole.DEPT_HEAD and user_role in ["dept_head", "faculty"]:
            return True
        if role == UserRole.REGISTRAR and user_role == "registrar":
            return True
        if role == UserRole.STUDENT and user_role == "student":
            return True
    return False


def role_required(*allowed_roles):
    """
    Decorator for views requiring specific user roles.
    Redirects unauthenticated users to login;
    Returns HTTP 403 Forbidden with custom 403 template if role is disallowed.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("accounts:login")

            if not user_has_role(request.user, *allowed_roles):
                return render(
                    request,
                    "403.html",
                    {
                        "message": "You do not have permission to access this resource.",
                        "required_roles": [str(r) for r in allowed_roles],
                        "current_role": getattr(getattr(request.user, "profile", None), "get_role_display", lambda: "Unknown")(),
                    },
                    status=403,
                )
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def scope_for(user, queryset_or_model, dept_field="department"):
    """
    Enforces data scoping in database queries so that:
    - Admin & Registrar: See all records
    - Department Head: Scoped strictly to their own department (raises 403 / empty if unassigned)
    - Student: Scoped strictly to their own student profile
    """
    from apps.academic.models import Student, Grade, Attendance, Course
    
    # Check if queryset or model class passed
    if hasattr(queryset_or_model, "objects"):
        qs = queryset_or_model.objects.all()
        model_cls = queryset_or_model
    else:
        qs = queryset_or_model
        model_cls = qs.model

    if not user.is_authenticated:
        return qs.none()

    if user.is_superuser:
        return qs

    profile = getattr(user, "profile", None)
    if not profile:
        return qs.none()

    # Admin & Registrar: Global scope
    if profile.role in [UserRole.ADMIN, "analyst"] or user.is_staff:
        return qs
    if profile.role == UserRole.REGISTRAR:
        return qs

    # Department Head: Scoped to their department
    if profile.role in [UserRole.DEPT_HEAD, "faculty"]:
        dept = get_user_department(user)
        if not dept:
            # Fallback filter by name string match if Department record not yet linked
            dept_name = profile.department
            if hasattr(model_cls, dept_field):
                return qs.filter(**{f"{dept_field}__name__icontains": dept_name})
            elif hasattr(model_cls, "course"):
                return qs.filter(**{f"course__{dept_field}__name__icontains": dept_name})
            elif hasattr(model_cls, "student"):
                return qs.filter(**{f"student__{dept_field}__name__icontains": dept_name})
            return qs.none()

        if hasattr(model_cls, dept_field):
            return qs.filter(**{dept_field: dept})
        elif hasattr(model_cls, "course"):
            return qs.filter(**{f"course__{dept_field}": dept})
        elif hasattr(model_cls, "student"):
            return qs.filter(**{f"student__{dept_field}": dept})
        return qs

    # Student: Scoped strictly to their own record
    if profile.role == UserRole.STUDENT:
        # Check student linked by user
        student = Student.objects.filter(user=user).first()
        if not student:
            # Check by username as student_id or email
            student = Student.objects.filter(models.Q(student_id__iexact=user.username) | models.Q(email__iexact=user.email)).first()
            if student and not student.user:
                student.user = user
                student.save(update_fields=["user"])

        if not student:
            return qs.none()

        if model_cls == Student:
            return qs.filter(id=student.id)
        elif hasattr(model_cls, "student"):
            return qs.filter(student=student)
        elif model_cls == Course:
            # Courses the student is enrolled in (via grades)
            course_ids = Grade.objects.filter(student=student).values_list("course_id", flat=True)
            return qs.filter(id__in=course_ids)

    return qs.none()
