from django.contrib import admin
from apps.uploads.models import Upload, Sheet, ColumnProfile, CleaningAction, QualityReport


@admin.register(Upload)
class UploadAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "owner", "status", "quality_score", "row_count_clean", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("original_filename", "owner__username", "id")


@admin.register(ColumnProfile)
class ColumnProfileAdmin(admin.ModelAdmin):
    list_display = ("name_clean", "upload", "role", "inferred_type", "missing_pct_after", "outlier_count")
    list_filter = ("role", "inferred_type")
    search_fields = ("name_clean", "name_raw")


@admin.register(CleaningAction)
class CleaningActionAdmin(admin.ModelAdmin):
    list_display = ("rule_id", "rule_name", "upload", "column", "severity")
    list_filter = ("rule_id", "severity")
    search_fields = ("rule_id", "rule_name", "column", "reason")


@admin.register(QualityReport)
class QualityReportAdmin(admin.ModelAdmin):
    list_display = ("upload", "quality_score", "completeness_score", "validity_score", "uniqueness_score", "consistency_score")
