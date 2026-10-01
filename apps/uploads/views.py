"""
Upload views: listing, upload creation, live processing, and data downloads.
"""

import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, Http404, FileResponse
from django.views.decorators.http import require_POST
from apps.uploads.models import Upload, UploadStatus, QualityReport, ColumnProfile, CleaningAction
from apps.uploads.forms import UploadForm
from apps.uploads.tasks import trigger_upload_processing


@login_required
def upload_list_view(request):
    """List all uploads belonging to the current user (O6 user data isolation)."""
    uploads = Upload.objects.filter(owner=request.user)
    return render(request, "uploads/list.html", {"uploads": uploads})


@login_required
def upload_create_view(request):
    """Upload a new Excel spreadsheet with custom cleaning parameters."""
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data["file"]
            config_options = {
                "fuzzy_threshold": form.cleaned_data["fuzzy_threshold"],
                "outlier_method": form.cleaned_data["outlier_method"],
                "missing_numeric_strategy": form.cleaned_data["missing_numeric_strategy"],
                "missing_category_strategy": form.cleaned_data["missing_category_strategy"],
                "ambiguous_date_preference": form.cleaned_data["ambiguous_date_preference"],
            }

            upload_record = Upload.objects.create(
                owner=request.user,
                original_filename=uploaded_file.name,
                stored_file=uploaded_file,
                size_bytes=uploaded_file.size,
                status=UploadStatus.QUEUED,
                config_options=config_options,
            )

            # Trigger async processing thread
            trigger_upload_processing(str(upload_record.id), async_mode=True)
            messages.success(request, f"File '{uploaded_file.name}' uploaded successfully. Processing started.")
            return redirect("uploads:processing", upload_id=upload_record.id)
    else:
        form = UploadForm()

    return render(request, "uploads/new.html", {"form": form})


@login_required
def upload_processing_view(request, upload_id):
    """Live processing page with real-time polling updates (L2 live behavior)."""
    upload = get_object_or_404(Upload, id=upload_id, owner=request.user)

    if upload.status == UploadStatus.DONE:
        return redirect("uploads:report", upload_id=upload.id)

    return render(request, "uploads/processing.html", {"upload": upload})


@login_required
def upload_report_view(request, upload_id):
    """Comprehensive Data Quality Report page with before/after statistics and action logs."""
    upload = get_object_or_404(Upload, id=upload_id, owner=request.user)

    if upload.status == UploadStatus.PROCESSING:
        return redirect("uploads:processing", upload_id=upload.id)
    elif upload.status == UploadStatus.FAILED:
        messages.error(request, f"Processing failed: {upload.error_message}")
        return redirect("uploads:list")

    report = getattr(upload, "report", None)
    profiles = upload.column_profiles.all().order_by("id")
    actions = upload.actions.all().order_by("id")

    return render(
        request,
        "uploads/report.html",
        {
            "upload": upload,
            "report": report,
            "profiles": profiles,
            "actions": actions,
        },
    )


@login_required
def upload_download_view(request, upload_id):
    """Secure download endpoint for raw and cleaned files."""
    upload = get_object_or_404(Upload, id=upload_id, owner=request.user)
    version = request.GET.get("version", "clean_xlsx")

    if version == "raw":
        if not upload.stored_file or not os.path.exists(upload.stored_file.path):
            raise Http404("Original raw file not found.")
        response = FileResponse(open(upload.stored_file.path, "rb"), as_attachment=True, filename=f"raw_{upload.original_filename}")
        return response

    elif version == "clean_csv":
        if not upload.cleaned_csv or not os.path.exists(upload.cleaned_csv.path):
            raise Http404("Cleaned CSV file not ready or not found.")
        base_name = os.path.splitext(upload.original_filename)[0]
        response = FileResponse(open(upload.cleaned_csv.path, "rb"), as_attachment=True, filename=f"{base_name}_cleaned.csv")
        return response

    else:  # clean_xlsx
        if not upload.cleaned_file or not os.path.exists(upload.cleaned_file.path):
            raise Http404("Cleaned XLSX file not ready or not found.")
        base_name = os.path.splitext(upload.original_filename)[0]
        response = FileResponse(open(upload.cleaned_file.path, "rb"), as_attachment=True, filename=f"{base_name}_cleaned.xlsx")
        return response


@login_required
@require_POST
def upload_rerun_view(request, upload_id):
    """Re-run the cleaning pipeline on the stored raw file with updated parameters."""
    upload = get_object_or_404(Upload, id=upload_id, owner=request.user)

    fuzzy_threshold = int(request.POST.get("fuzzy_threshold", 85))
    outlier_method = request.POST.get("outlier_method", "iqr")
    missing_numeric = request.POST.get("missing_numeric_strategy", "flag")
    missing_category = request.POST.get("missing_category_strategy", "flag")

    upload.config_options = {
        "fuzzy_threshold": fuzzy_threshold,
        "outlier_method": outlier_method,
        "missing_numeric_strategy": missing_numeric,
        "missing_category_strategy": missing_category,
    }
    upload.status = UploadStatus.QUEUED
    upload.progress_pct = 0
    upload.current_step = "Re-queued for processing"
    upload.save()

    trigger_upload_processing(str(upload.id), async_mode=True)
    messages.info(request, "Cleaning pipeline re-triggered with updated configuration.")
    return redirect("uploads:processing", upload_id=upload.id)


@login_required
@require_POST
def upload_delete_view(request, upload_id):
    """Delete an upload and associated files."""
    upload = get_object_or_404(Upload, id=upload_id, owner=request.user)
    name = upload.original_filename

    # Delete disk files
    try:
        if upload.stored_file and os.path.exists(upload.stored_file.path):
            os.remove(upload.stored_file.path)
        if upload.cleaned_file and os.path.exists(upload.cleaned_file.path):
            os.remove(upload.cleaned_file.path)
        if upload.cleaned_csv and os.path.exists(upload.cleaned_csv.path):
            os.remove(upload.cleaned_csv.path)
    except Exception:
        pass

    upload.delete()
    messages.success(request, f"Upload '{name}' deleted successfully.")
    return redirect("uploads:list")
