def scope_for(user, queryset, dept_field='department', student_field='student'):
    """
    Role-based query scoping utility.
    - Admin & Registrar: University-wide view of all data.
    - Dept Head / Lecturer: Scoped exclusively to their department.
    - Student: Scoped strictly to their own student record.
    """
    if not user or not user.is_authenticated:
        return queryset.none()

    if user.is_superuser:
        return queryset

    profile = getattr(user, 'profile', None)
    if not profile:
        return queryset.none()

    # Admin & Registrar see all data
    if profile.is_admin or profile.is_registrar:
        return queryset

    # Dept Head sees only their assigned department
    if profile.is_dept_head:
        if not profile.department:
            return queryset.none()
        filter_kwargs = {dept_field: profile.department}
        return queryset.filter(**filter_kwargs)

    # Student sees only their own records
    if profile.is_student:
        if queryset.model.__name__ == 'Student':
            return queryset.filter(id=profile.student_record.id) if profile.student_record else queryset.none()
        elif queryset.model.__name__ == 'Course':
            if profile.student_record and profile.student_record.program:
                return queryset.filter(department=profile.student_record.program.department)
            elif profile.department:
                return queryset.filter(department=profile.department)
            return queryset.all()

        # For models with direct student field (e.g. Enrollment, Attendance)
        model_field_names = [f.name for f in queryset.model._meta.get_fields()]
        if student_field in model_field_names:
            if not profile.student_record:
                return queryset.none()
            filter_kwargs = {student_field: profile.student_record}
            return queryset.filter(**filter_kwargs)

        return queryset.all()

    return queryset.none()
