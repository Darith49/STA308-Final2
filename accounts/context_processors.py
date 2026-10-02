from .models import Role

def user_role_context(request):
    """
    Context processor adding current user profile and role flags to templates.
    """
    if not request.user.is_authenticated:
        return {
            'current_profile': None,
            'is_admin': False,
            'is_registrar': False,
            'is_dept_head': False,
            'is_student': False,
            'can_upload': False,
            'can_manage_users': False,
            'user_department': None,
        }

    profile = getattr(request.user, 'profile', None)
    if not profile:
        return {
            'current_profile': None,
            'is_admin': request.user.is_superuser,
            'is_registrar': False,
            'is_dept_head': False,
            'is_student': False,
            'can_upload': request.user.is_superuser,
            'can_manage_users': request.user.is_superuser,
            'user_department': None,
        }

    user_dept = profile.department
    if not user_dept and profile.is_student and profile.student_record and profile.student_record.program:
        user_dept = profile.student_record.program.department

    return {
        'current_profile': profile,
        'is_admin': profile.is_admin,
        'is_registrar': profile.is_registrar,
        'is_dept_head': profile.is_dept_head,
        'is_student': profile.is_student,
        'can_upload': profile.can_upload,
        'can_manage_users': profile.can_manage_users,
        'user_department': user_dept,
    }
