"""
Accounts models: User Profile extension with roles and departments.
"""

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserRole(models.TextChoices):
    STUDENT = "student", "Student"
    FACULTY = "faculty", "Faculty / Researcher"
    DATA_ANALYST = "analyst", "Data Analyst"
    ADMINISTRATOR = "admin", "Administrator"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.DATA_ANALYST)
    department = models.CharField(max_length=150, default="Department of Statistics & Data Science")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        if hasattr(instance, "profile"):
            instance.profile.save()
