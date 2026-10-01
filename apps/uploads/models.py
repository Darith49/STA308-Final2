"""
Upload, Sheet, ColumnProfile, CleaningAction, and QualityReport models.
"""

import uuid
import os
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


def upload_path_handler(instance, filename):
    """Store raw files under media/uploads/<uuid>.xlsx to prevent path traversal."""
    ext = os.path.splitext(filename)[1].lower() or ".xlsx"
    return f"uploads/{instance.id}{ext}"


def cleaned_path_handler(instance, filename):
    """Store cleaned files under media/cleaned/<uuid>_clean.xlsx."""
    ext = os.path.splitext(filename)[1].lower() or ".xlsx"
    return f"cleaned/{instance.id}_clean{ext}"


class UploadStatus(models.TextChoices):
    QUEUED = "QUEUED", "Queued"
    PROCESSING = "PROCESSING", "Processing"
    DONE = "DONE", "Done"
    FAILED = "FAILED", "Failed"


class Upload(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="uploads")
    original_filename = models.CharField(max_length=255)
    stored_file = models.FileField(upload_to=upload_path_handler)
    cleaned_file = models.FileField(upload_to=cleaned_path_handler, null=True, blank=True)
    cleaned_csv = models.FileField(upload_to=cleaned_path_handler, null=True, blank=True)
    sha256 = models.CharField(max_length=64, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    status = models.CharField(max_length=20, choices=UploadStatus.choices, default=UploadStatus.QUEUED)
    current_step = models.CharField(max_length=255, default="Upload queued for processing")
    progress_pct = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    
    # Dataset statistics
    row_count_raw = models.IntegerField(default=0)
    row_count_clean = models.IntegerField(default=0)
    col_count_raw = models.IntegerField(default=0)
    col_count_clean = models.IntegerField(default=0)
    quality_score = models.FloatField(null=True, blank=True)
    config_options = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_filename} ({self.status})"

    def mark_processing(self, step_name="Starting cleaning pipeline..."):
        self.status = UploadStatus.PROCESSING
        self.current_step = step_name
        self.progress_pct = 5
        self.save(update_fields=["status", "current_step", "progress_pct"])

    def mark_done(self, quality_score, row_raw, row_clean, col_raw, col_clean):
        self.status = UploadStatus.DONE
        self.current_step = "Cleaning and analysis complete"
        self.progress_pct = 100
        self.quality_score = quality_score
        self.row_count_raw = row_raw
        self.row_count_clean = row_clean
        self.col_count_raw = col_raw
        self.col_count_clean = col_clean
        self.finished_at = timezone.now()
        self.save()

    def mark_failed(self, error_text):
        self.status = UploadStatus.FAILED
        self.error_message = error_text
        self.current_step = "Processing failed"
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "error_message", "current_step", "finished_at"])


class Sheet(models.Model):
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, related_name="sheets")
    name = models.CharField(max_length=150)
    header_row = models.IntegerField(default=0)
    n_rows = models.IntegerField(default=0)
    n_cols = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.name} (Upload: {self.upload_id})"


class ColumnProfile(models.Model):
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, related_name="column_profiles")
    sheet = models.ForeignKey(Sheet, on_delete=models.SET_NULL, null=True, blank=True)
    name_raw = models.CharField(max_length=200)
    name_clean = models.CharField(max_length=200)
    inferred_type = models.CharField(max_length=50)
    role = models.CharField(max_length=50, default="text")
    missing_pct_before = models.FloatField(default=0.0)
    missing_pct_after = models.FloatField(default=0.0)
    n_unique = models.IntegerField(default=0)
    unique_sample = models.JSONField(default=list, blank=True)
    
    # Statistical measures
    min_val = models.FloatField(null=True, blank=True)
    max_val = models.FloatField(null=True, blank=True)
    mean_val = models.FloatField(null=True, blank=True)
    std_val = models.FloatField(null=True, blank=True)
    median_val = models.FloatField(null=True, blank=True)
    iqr_val = models.FloatField(null=True, blank=True)
    skew_val = models.FloatField(null=True, blank=True)
    kurt_val = models.FloatField(null=True, blank=True)
    outlier_count = models.IntegerField(default=0)
    normality_test = models.CharField(max_length=150, blank=True)
    normality_hint = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name_clean} ({self.role})"


class CleaningAction(models.Model):
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, related_name="actions")
    sheet = models.CharField(max_length=150, default="Sheet1")
    rule_id = models.CharField(max_length=20)
    rule_name = models.CharField(max_length=100)
    column = models.CharField(max_length=200, blank=True)
    row_ref = models.IntegerField(null=True, blank=True)
    before_value = models.TextField(blank=True)
    after_value = models.TextField(blank=True)
    reason = models.TextField()
    severity = models.CharField(max_length=20, default="info")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"[{self.rule_id}] {self.rule_name} - {self.column}"


class QualityReport(models.Model):
    upload = models.OneToOneField(Upload, on_delete=models.CASCADE, related_name="report")
    summary_json = models.JSONField(default=dict)
    correlation_json = models.JSONField(default=dict)
    quality_score = models.FloatField(default=0.0)
    completeness_score = models.FloatField(default=0.0)
    validity_score = models.FloatField(default=0.0)
    uniqueness_score = models.FloatField(default=0.0)
    consistency_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Quality Report ({self.quality_score:.1f}) for {self.upload_id}"
