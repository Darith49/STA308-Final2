"""
Upload views: listing, upload creation, live processing, report review,
template downloading, error file generation, and atomic deletion rollbacks.
"""

import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, Http404, FileResponse
from django.views.decorators.http import require_POST

from apps.uploads.models import Upload, UploadStatus, QualityReport, ColumnProfile, CleaningAction, UploadError, DatasetType
from apps.uploads.forms import UploadForm
from apps.uploads.tasks import trigger_upload_processing
from apps.uploads.templates_generator import generate_dataset_template
from apps.accounts.models import log_audit_event, UserRole
from apps.academic.scoping import role_required


@login_required
def upload_list_view(request):
    """
    List uploads.
    - Admin: can view all uploads across the system.
    - Registrar / Analyst: views their own uploads (or all if specified).
    """
    profile = getattr(request.user, "profile", None)
    is_admin = profile.is_admin if profile else request.user.is_superuser

    dataset_filter = request.GET.get("dataset_type", "")
    
    if is_admin:
        uploads = Upload.objects.all()
    else:
        uploads = Upload.objects.filter(owner=request.user)

    if dataset_filter and dataset_filter != "all":
        uploads = uploads.filter(dataset_type=dataset_filter)

    return render(
        request,
        "uploads/list.html",
        {
            "uploads": uploads,
            "is_admin": is_admin,
            "dataset_filter": dataset_filter,
            "dataset_types": DatasetType.choices,
        },
    )


@login_required
@role_required(UserRole.ADMIN, UserRole.REGISTRAR, UserRole.DATA_ANALYST)
def upload_create_view(request):
    """Upload a new Excel spreadsheet with dataset type and cleaning configuration."""
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data["file"]
            dataset_type = form.cleaned_data.get("dataset_type", DatasetType.GENERIC)
            sha256 = form.cleaned_data.get("sha256", "")

            config_options = {
                "fuzzy_threshold": form.cleaned_data["fuzzy_threshold"],
                "outlier_method": form.cleaned_data["outlier_method"],
                "missing_numeric_strategy": form.cleaned_data["missing_numeric_strategy"],
                "missing_category_strategy": form.cleaned_data["missing_category_strategy"],
                "ambiguous_date_preference": form.cleaned_data["ambiguous_date_preference"],
            }

            upload_record = Upload.objects.create(
                owner=request.user,
                dataset_type=dataset_type,
                original_filename=uploaded_file.name,
                stored_file=uploaded_file,
                sha256=sha256,
                size_bytes=uploaded_file.size,
                status=UploadStatus.QUEUED,
                config_options=config_options,
            )

            # Audit log
            log_audit_event(
                request.user,
                "UPLOAD",
                target_model="Upload",
                target_id=str(upload_record.id),
                details=f"Uploaded {dataset_type} dataset: {uploaded_file.name} ({uploaded_file.size} bytes)",
                request=request,
            )

            # Trigger async processing thread
            trigger_upload_processing(str(upload_record.id), async_mode=True)
            messages.success(request, f"File '{uploaded_file.name}' accepted. Validating and cleaning pipeline running...")
            return redirect("uploads:processing", upload_id=upload_record.id)
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, err)
    else:
        initial_type = request.GET.get("type", DatasetType.COURSES)
        form = UploadForm(initial={"dataset_type": initial_type})

    return render(request, "uploads/new.html", {"form": form})


@login_required
def upload_processing_view(request, upload_id):
    """Live processing page with real-time polling updates."""
    profile = getattr(request.user, "profile", None)
    is_admin = profile.is_admin if profile else request.user.is_superuser

    if is_admin:
        upload = get_object_or_404(Upload, id=upload_id)
    else:
        upload = get_object_or_404(Upload, id=upload_id, owner=request.user)

    if upload.status == UploadStatus.DONE:
        return redirect("uploads:report", upload_id=upload.id)

    return render(request, "uploads/processing.html", {"upload": upload})


@login_required
def upload_report_view(request, upload_id):
    """Comprehensive Data Quality Report page with before/after statistics and action logs."""
    profile = getattr(request.user, "profile", None)
    is_admin = profile.is_admin if profile else request.user.is_superuser

    if is_admin:
        upload = get_object_or_404(Upload, id=upload_id)
    else:
        upload = get_object_or_404(Upload, id=upload_id, owner=request.user)

    if upload.status == UploadStatus.PROCESSING:
        return redirect("uploads:processing", upload_id=upload.id)
    elif upload.status == UploadStatus.FAILED:
        messages.error(request, f"Processing failed: {upload.error_message}")
        return redirect("uploads:list")

    report = getattr(upload, "report", None)
    profiles = upload.column_profiles.all().order_by("id")
    actions = upload.actions.all().order_by("id")
    errors = upload.errors.all().order_by("row_number")

    return render(
        request,
        "uploads/report.html",
        {
            "upload": upload,
            "report": report,
            "profiles": profiles,
            "actions": actions,
            "errors": errors,
            "error_count": errors.count(),
        },
    )


@login_required
def upload_download_view(request, upload_id):
    """Secure download endpoint for raw and cleaned files."""
    profile = getattr(request.user, "profile", None)
    is_admin = profile.is_admin if profile else request.user.is_superuser

    if is_admin:
        upload = get_object_or_404(Upload, id=upload_id)
    else:
        upload = get_object_or_404(Upload, id=upload_id, owner=request.user)

    version = request.GET.get("version", "clean_xlsx")

    if version == "raw":
        if not upload.stored_file or not os.path.exists(upload.stored_file.path):
            raise Http404("Original raw file not found.")
        return FileResponse(open(upload.stored_file.path, "rb"), as_attachment=True, filename=f"raw_{upload.original_filename}")

    elif version == "clean_csv":
        if not upload.cleaned_csv or not os.path.exists(upload.cleaned_csv.path):
            raise Http404("Cleaned CSV file not ready or not found.")
        base_name = os.path.splitext(upload.original_filename)[0]
        return FileResponse(open(upload.cleaned_csv.path, "rb"), as_attachment=True, filename=f"{base_name}_cleaned.csv")

    else:  # clean_xlsx
        if not upload.cleaned_file or not os.path.exists(upload.cleaned_file.path):
            raise Http404("Cleaned XLSX file not ready or not found.")
        base_name = os.path.splitext(upload.original_filename)[0]
        return FileResponse(open(upload.cleaned_file.path, "rb"), as_attachment=True, filename=f"{base_name}_cleaned.xlsx")


@login_required
def upload_error_file_view(request, upload_id):
    """Download an Excel (.xlsx) file containing all rejected rows with row number, column, and reason."""
    profile = getattr(request.user, "profile", None)
    is_admin = profile.is_admin if profile else request.user.is_superuser

    if is_admin:
        upload = get_object_or_404(Upload, id=upload_id)
    else:
        upload = get_object_or_404(Upload, id=upload_id, owner=request.user)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rejected Rows"
    ws.views.sheetView[0].showGridLines = True

    # Styling
    err_fill = PatternFill(start_color="991B1B", end_color="991B1B", fill_type="solid")
    err_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    border_thin = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    headers = ["Row Number", "Column Name", "Rejected Value", "Rejection Reason"]
    ws.append(headers)
    for col_idx in range(1, 5):
        c = ws.cell(row=1, column=col_idx)
        c.fill = err_fill
        c.font = err_font
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = border_thin

    errors = upload.errors.all().order_by("row_number")
    if not errors.exists():
        ws.append(["-", "None", "N/A", "No rejected rows - all records imported successfully!"])
    else:
        for err in errors:
            ws.append([err.row_number, err.column_name, str(err.raw_value), err.reason])
            for col_idx in range(1, 5):
                ws.cell(row=ws.max_row, column=col_idx).border = border_thin

    ws.column_dimensions["A"].width = 15
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 30
    ws.column_dimensions["D"].width = 60

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    base_name = os.path.splitext(upload.original_filename)[0]
    response["Content-Disposition"] = f'attachment; filename="{base_name}_rejected_errors.xlsx"'
    wb.save(response)
    return response


@login_required
def dataset_template_view(request, dataset_type):
    """Download starter templates with headers, sample row, and notes sheet for the Registrar."""
    try:
        buf = generate_dataset_template(dataset_type.lower())
        response = HttpResponse(
            buf.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{dataset_type.lower()}_template.xlsx"'
        return response
    except ValueError:
        raise Http404(f"Template for '{dataset_type}' not found.")


@login_required
@require_POST
def upload_rerun_view(request, upload_id):
    """Re-run the cleaning pipeline on the stored raw file with updated parameters."""
    profile = getattr(request.user, "profile", None)
    is_admin = profile.is_admin if profile else request.user.is_superuser

    if is_admin:
        upload = get_object_or_404(Upload, id=upload_id)
    else:
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
    """
    Delete an upload and roll back all rows linked to it.
    Admin can delete any upload; Registrar can delete their own upload.
    """
    profile = getattr(request.user, "profile", None)
    is_admin = profile.is_admin if profile else request.user.is_superuser

    if is_admin:
        upload = get_object_or_404(Upload, id=upload_id)
    else:
        upload = get_object_or_404(Upload, id=upload_id, owner=request.user)

    name = upload.original_filename
    dtype = upload.get_dataset_type_display()

    # Count domain rows that will be cascaded / rolled back
    c_count = upload.course_records.count()
    s_count = upload.student_records.count()
    g_count = upload.grade_records.count()
    a_count = upload.attendance_records.count()
    total_rolled_back = c_count + s_count + g_count + a_count

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

    # Audit log entry before deletion
    log_audit_event(
        request.user,
        "DELETE_UPLOAD",
        target_model="Upload",
        target_id=str(upload.id),
        details=f"Deleted {dtype} upload '{name}'. Rolled back {total_rolled_back} imported rows (Courses: {c_count}, Students: {s_count}, Grades: {g_count}, Attendance: {a_count}).",
        request=request,
    )

    upload.delete()
    messages.success(
        request,
        f"Upload '{name}' deleted successfully. All {total_rolled_back} linked records have been rolled back.",
    )
    return redirect("uploads:list")
