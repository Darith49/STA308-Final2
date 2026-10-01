from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile, Role

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        role = Role.ADMIN if instance.is_superuser else Role.DEPT_HEAD
        Profile.objects.create(user=instance, role=role)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
        else:
            role = Role.ADMIN if instance.is_superuser else Role.DEPT_HEAD
            Profile.objects.create(user=instance, role=role)
