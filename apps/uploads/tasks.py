"""
Processing task executor for uploaded spreadsheets.
Executes the data cleaning pipeline, saves cleaned artifacts,
and records statistical profiles and action logs in the database.
"""

import os
import io
import hashlib
import threading
import pandas as pd
from django.utils import timezone
from django.conf import settings
from apps.uploads.models import Upload, Sheet, ColumnProfile, CleaningAction, QualityReport, UploadStatus
from apps.uploads.validators import sanitize_formula_injection
from apps.cleaning.pipeline import DataCleaningPipeline
from apps.cleaning.types import CleaningConfig


def run_pipeline_for_upload(upload_id: str):
    """
    Worker function that loads the uploaded file, executes the cleaning pipeline,
    persists results to the database, and exports sanitized cleaned files.
    """
    try:
        upload = Upload.objects.get(id=upload_id)
    except Upload.DoesNotExist:
        return

    try:
        upload.mark_processing("Initializing cleaning pipeline...")

        # Construct CleaningConfig from upload options if provided
        opts = upload.config_options or {}
        cfg = CleaningConfig(
            fuzzy_threshold=float(opts.get("fuzzy_threshold", 85.0)),
            outlier_method=str(opts.get("outlier_method", "iqr")),
            missing_numeric_strategy=str(opts.get("missing_numeric_strategy", "flag")),
            missing_category_strategy=str(opts.get("missing_category_strategy", "flag")),
            ambiguous_date_preference=str(opts.get("ambiguous_date_preference", "DMY")),
        )

        def progress_callback(pct: int, step_desc: str):
            upload.progress_pct = pct
            upload.current_step = step_desc
            upload.save(update_fields=["progress_pct", "current_step"])

        file_path = upload.stored_file.path

        # Compute sha256 checksum
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        upload.sha256 = hasher.hexdigest()
        upload.size_bytes = os.path.getsize(file_path)
        upload.save(update_fields=["sha256", "size_bytes"])

        # Execute pure Python cleaning pipeline
        pipeline = DataCleaningPipeline(config=cfg)
        result = pipeline.run_file(
            file_path_or_buffer=file_path,
            progress_callback=progress_callback
        )

        clean_df = result.clean_df
        raw_df = result.raw_df
        report_data = result.report

        # Persist sheet info
        Sheet.objects.filter(upload=upload).delete()
        sheet_obj = Sheet.objects.create(
            upload=upload,
            name=result.current_sheet,
            header_row=0,
            n_rows=len(clean_df),
            n_cols=len(clean_df.columns),
        )

        # Persist column profiles
        ColumnProfile.objects.filter(upload=upload).delete()
        col_profile_objs = []
        for col_name, p in report_data.column_profiles.items():
            col_profile_objs.append(
                ColumnProfile(
                    upload=upload,
                    sheet=sheet_obj,
                    name_raw=p.name_raw,
                    name_clean=p.name_clean,
                    inferred_type=p.inferred_type,
                    role=p.role,
                    missing_pct_before=p.missing_pct_before,
                    missing_pct_after=p.missing_pct_after,
                    n_unique=p.n_unique,
                    unique_sample=p.unique_sample,
                    min_val=p.min_val,
                    max_val=p.max_val,
                    mean_val=p.mean_val,
                    std_val=p.std_val,
                    median_val=p.median_val,
                    iqr_val=p.iqr_val,
                    skew_val=p.skew_val,
                    kurt_val=p.kurt_val,
                    outlier_count=p.outlier_count,
                    normality_test=p.normality_test,
                    normality_hint=p.normality_hint,
                )
            )
        ColumnProfile.objects.bulk_create(col_profile_objs)

        # Persist cleaning action log
        CleaningAction.objects.filter(upload=upload).delete()
        action_objs = [
            CleaningAction(
                upload=upload,
                sheet=a.sheet_name,
                rule_id=a.rule_id,
                rule_name=a.rule_name,
                column=a.column or "",
                row_ref=a.row_ref,
                before_value=str(a.before_value or "")[:500],
                after_value=str(a.after_value or "")[:500],
                reason=a.reason,
                severity=a.severity,
            )
            for a in report_data.actions_log
        ]
        CleaningAction.objects.bulk_create(action_objs)

        # Persist QualityReport
        QualityReport.objects.filter(upload=upload).delete()
        QualityReport.objects.create(
            upload=upload,
            summary_json=report_data.to_dict(),
            correlation_json=report_data.correlation_matrix,
            quality_score=report_data.overall_score,
            completeness_score=report_data.completeness_score,
            validity_score=report_data.validity_score,
            uniqueness_score=report_data.uniqueness_score,
            consistency_score=report_data.consistency_score,
        )

        # Apply formula injection sanitization on cleaned output
        sanitized_df = clean_df.copy()
        for c in sanitized_df.columns:
            if sanitized_df[c].dtype == object or pd.api.types.is_string_dtype(sanitized_df[c]):
                sanitized_df[c] = sanitized_df[c].apply(sanitize_formula_injection)

        # Save cleaned file artifacts
        cleaned_dir = os.path.join(settings.MEDIA_ROOT, "cleaned")
        os.makedirs(cleaned_dir, exist_ok=True)

        clean_xlsx_filename = f"{upload.id}_clean.xlsx"
        clean_xlsx_path = os.path.join(cleaned_dir, clean_xlsx_filename)
        
        # Write clean XLSX with a dedicated 'Clean Data' sheet and a 'Cleaning Log' sheet!
        with pd.ExcelWriter(clean_xlsx_path, engine="openpyxl") as writer:
            sanitized_df.to_excel(writer, sheet_name="Clean Data", index=False)
            # Create Cleaning Log sheet for auditability
            log_df = pd.DataFrame([a.to_dict() for a in report_data.actions_log])
            if not log_df.empty:
                log_df.to_excel(writer, sheet_name="Cleaning Log", index=False)

        clean_csv_filename = f"{upload.id}_clean.csv"
        clean_csv_path = os.path.join(cleaned_dir, clean_csv_filename)
        sanitized_df.to_csv(clean_csv_path, index=False)

        upload.cleaned_file.name = f"cleaned/{clean_xlsx_filename}"
        upload.cleaned_csv.name = f"cleaned/{clean_csv_filename}"

        # Mark done
        upload.mark_done(
            quality_score=report_data.overall_score,
            row_raw=report_data.raw_rows,
            row_clean=report_data.clean_rows,
            col_raw=report_data.raw_cols,
            col_clean=report_data.clean_cols,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        upload.mark_failed(str(e))


def trigger_upload_processing(upload_id: str, async_mode: bool = True):
    """Trigger processing either in a background thread or synchronously."""
    if async_mode:
        t = threading.Thread(target=run_pipeline_for_upload, args=(upload_id,), daemon=True)
        t.start()
        return t
    else:
        run_pipeline_for_upload(upload_id)
        return None
