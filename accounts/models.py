from django.db import models
from django.contrib.auth.models import User

class Role(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    REGISTRAR = 'registrar', 'Registrar'
    DEPT_HEAD = 'dept_head', 'Dept Head / Lecturer'
    STUDENT = 'student', 'Student'

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.DEPT_HEAD)
    department = models.ForeignKey(
        'academics.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_profiles',
        help_text="Assigned department (required for Department Heads/Lecturers)"
    )
    student_record = models.OneToOneField(
        'academics.Student',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_profile',
        help_text="Linked student record for student role accounts"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        dept_str = f" ({self.department.code})" if self.department else ""
        return f"{self.user.username} - {self.get_role_display()}{dept_str}"

    @property
    def is_admin(self):
        return self.role == Role.ADMIN or self.user.is_superuser

    @property
    def is_registrar(self):
        return self.role == Role.REGISTRAR

    @property
    def is_dept_head(self):
        return self.role == Role.DEPT_HEAD

    @property
    def is_student(self):
        return self.role == Role.STUDENT

    @property
    def can_upload(self):
        return self.is_admin or self.is_registrar

    @property
    def can_manage_users(self):
        return self.is_admin

    def can_delete_upload(self, upload):
        if self.is_admin:
            return True
        if self.is_registrar and upload.uploaded_by == self.user:
            return True
        return False
