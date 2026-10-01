import os
import uuid
from django.db import models
from django.contrib.auth.models import User

def upload_file_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    random_filename = f"{uuid.uuid4().hex}{ext}"
    return os.path.join('uploads', random_filename)

class DatasetType(models.TextChoices):
    STUDENTS = 'students', 'Students'
    COURSES = 'courses', 'Courses'
    GRADES = 'grades', 'Grades'
    ATTENDANCE = 'attendance', 'Attendance'

class UploadStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    DONE = 'done', 'Done'
    FAILED = 'failed', 'Failed'

class Upload(models.Model):
    file = models.FileField(upload_to=upload_file_path)
    original_filename = models.CharField(max_length=255, blank=True)
    file_hash = models.CharField(max_length=64, db_index=True)
    dataset_type = models.CharField(max_length=20, choices=DatasetType.choices)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploads')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=UploadStatus.choices, default=UploadStatus.PENDING)
    report = models.JSONField(default=dict, blank=True)
    rows_in = models.PositiveIntegerField(default=0)
    rows_ok = models.PositiveIntegerField(default=0)
    rows_rejected = models.PositiveIntegerField(default=0)
    progress_percent = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.get_dataset_type_display()} upload by {self.uploaded_by.username} ({self.uploaded_at.strftime('%Y-%m-%d %H:%M')})"


class UploadError(models.Model):
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, related_name='errors')
    row_number = models.PositiveIntegerField()
    column = models.CharField(max_length=100, blank=True)
    value = models.TextField(blank=True, null=True)
    message = models.TextField()

    class Meta:
        ordering = ['row_number']

    def __str__(self):
        return f"Upload {self.upload_id} - Row {self.row_number}: {self.message}"


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=50)  # e.g., 'UPLOAD', 'ROLLBACK_DELETE', 'USER_CREATE'
    target = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        user_str = self.user.username if self.user else "System"
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {user_str} - {self.action}: {self.target}"
