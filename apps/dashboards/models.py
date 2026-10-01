"""
DashboardConfig model for storing user customized chart dashboards.
"""

from django.db import models
from django.contrib.auth.models import User
from apps.uploads.models import Upload


class DashboardConfig(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_dashboards")
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, related_name="dashboards")
    title = models.CharField(max_length=200, default="University Analytics Dashboard")
    description = models.TextField(blank=True)
    chart_configs = models.JSONField(default=list)  # List of customized chart widgets
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.title} ({self.upload.original_filename})"
