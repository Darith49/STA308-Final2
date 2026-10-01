"""
Accounts models: User Profile extension with roles, departments, and system Audit Logging.
"""

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserRole(models.TextChoices):
    ADMIN = "admin", "Admin (Full Control)"
    REGISTRAR = "registrar", "Registrar (Data Owner)"
    DEPT_HEAD = "dept_head", "Department Head / Lecturer"
    STUDENT = "student", "Student (Stretch Goal)"
    DATA_ANALYST = "analyst", "Data Analyst (Legacy)"
    FACULTY = "faculty", "Faculty / Researcher (Legacy)"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.STUDENT)
    department = models.CharField(max_length=150, default="Department of Statistics & Data Science")
    phone = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN or self.user.is_superuser

    @property
    def is_registrar(self):
        return self.role == UserRole.REGISTRAR

    @property
    def is_dept_head(self):
        return self.role in [UserRole.DEPT_HEAD, UserRole.FACULTY]

    @property
    def is_student(self):
        return self.role == UserRole.STUDENT


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("LOGIN", "User Login"),
        ("LOGOUT", "User Logout"),
        ("UPLOAD", "Dataset Upload"),
        ("DELETE_UPLOAD", "Delete Upload & Rollback"),
        ("USER_CREATE", "Create User"),
        ("USER_UPDATE", "Update User"),
        ("USER_DEACTIVATE", "Deactivate User"),
        ("USER_ACTIVATE", "Activate User"),
        ("PASSWORD_RESET", "Reset Password"),
        ("DEPT_CREATE", "Create Department"),
        ("DEPT_UPDATE", "Update Department"),
        ("DEPT_DELETE", "Delete Department"),
        ("PROGRAM_CREATE", "Create Program"),
        ("PROGRAM_DELETE", "Delete Program"),
        ("COURSE_CREATE", "Create Course"),
        ("COURSE_DELETE", "Delete Course"),
        ("EXPORT_CSV", "Export Scoped CSV"),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    target_model = models.CharField(max_length=50, blank=True)
    target_id = models.CharField(max_length=100, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.CharField(max_length=50, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        user_str = self.user.username if self.user else "System"
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {user_str} - {self.action} ({self.target_model}:{self.target_id})"


def log_audit_event(user, action, target_model="", target_id="", details="", request=None):
    """Utility function to append an entry to the immutable audit trail."""
    ip_address = ""
    if request:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(",")[0].strip()
        else:
            ip_address = request.META.get("REMOTE_ADDR", "")
    
    # If user is anonymous or None
    user_obj = user if (user and user.is_authenticated) else None

    return AuditLog.objects.create(
        user=user_obj,
        action=action,
        target_model=str(target_model),
        target_id=str(target_id),
        details=str(details),
        ip_address=ip_address,
    )


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        if hasattr(instance, "profile"):
            instance.profile.save()
