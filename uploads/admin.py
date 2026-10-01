from django.contrib import admin
from .models import Upload, UploadError, AuditLog

@admin.register(Upload)
class UploadAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_filename', 'dataset_type', 'uploaded_by', 'uploaded_at', 'status', 'rows_ok', 'rows_rejected')
    list_filter = ('dataset_type', 'status', 'uploaded_at')
    search_fields = ('original_filename', 'uploaded_by__username', 'file_hash')


@admin.register(UploadError)
class UploadErrorAdmin(admin.ModelAdmin):
    list_display = ('upload', 'row_number', 'column', 'value', 'message')
    list_filter = ('upload__dataset_type',)
    search_fields = ('message', 'value', 'column')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'target')
    list_filter = ('action', 'timestamp')
    search_fields = ('action', 'target', 'user__username')
