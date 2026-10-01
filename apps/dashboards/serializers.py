"""
Django REST Framework serializers for Uploads, ColumnProfiles, Reports, and Dashboards.
"""

from rest_framework import serializers
from apps.uploads.models import Upload, ColumnProfile, CleaningAction, QualityReport
from apps.dashboards.models import DashboardConfig


class ColumnProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColumnProfile
        fields = "__all__"


class CleaningActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CleaningAction
        fields = "__all__"


class QualityReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityReport
        fields = "__all__"


class UploadListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Upload
        fields = [
            "id",
            "original_filename",
            "size_bytes",
            "status",
            "progress_pct",
            "current_step",
            "quality_score",
            "row_count_raw",
            "row_count_clean",
            "col_count_clean",
            "created_at",
            "finished_at",
        ]


class UploadStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Upload
        fields = ["id", "status", "progress_pct", "current_step", "error_message"]


class DashboardConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardConfig
        fields = ["id", "upload", "title", "description", "chart_configs", "created_at", "updated_at"]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["owner"] = self.context["request"].user
        return super().create(validated_data)
