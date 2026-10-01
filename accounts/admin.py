from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'

class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'get_role', 'get_dept', 'is_staff')

    def get_role(self, instance):
        return instance.profile.get_role_display() if hasattr(instance, 'profile') else '-'
    get_role.short_description = 'Role'

    def get_dept(self, instance):
        return instance.profile.department.code if (hasattr(instance, 'profile') and instance.profile.department) else '-'
    get_dept.short_description = 'Department'

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Profile)
