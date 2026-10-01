from django.contrib import admin
from apps.accounts.models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "department", "created_at")
    list_filter = ("role", "department")
    search_fields = ("user__username", "user__email", "department")
