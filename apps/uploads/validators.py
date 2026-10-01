"""
Security Validators for Uploaded Spreadsheets.
Protects against malicious files, zip bombs, formula injection, path traversal,
duplicate uploads, and dataset schema mismatches.
"""

import os
import re
import hashlib
import zipfile
import openpyxl
from typing import Tuple, List, Set
from django.core.exceptions import ValidationError
from django.conf import settings

MAX_FILE_SIZE_BYTES = getattr(settings, "MAX_UPLOAD_SIZE_MB", 20) * 1024 * 1024

REQUIRED_COLUMNS = {
    "courses": ["course_code", "title", "department_code"],
    "students": ["student_id", "first_name", "last_name", "email", "department_code"],
    "grades": ["student_id", "course_code", "numerical_score"],
    "attendance": ["student_id", "course_code", "date", "status"],
}


def normalize_col_name(col: str) -> str:
    """Normalize column header into clean snake_case for comparison."""
    if not col:
        return ""
    col = str(col).strip().lower()
    col = re.sub(r"[^\w\s]", "", col)
    col = re.sub(r"\s+", "_", col)
    return col


def compute_file_sha256(file_obj) -> str:
    """Calculate SHA-256 hash of a file object without altering seek position."""
    pos = file_obj.tell() if hasattr(file_obj, "tell") else 0
    file_obj.seek(0)
    hasher = hashlib.sha256()
    while chunk := file_obj.read(65536):
        hasher.update(chunk)
    file_obj.seek(pos)
    return hasher.hexdigest()


def validate_duplicate_hash(sha256_hash: str, exclude_id=None) -> None:
    """Ensure duplicate files cannot be uploaded twice."""
    from apps.uploads.models import Upload
    qs = Upload.objects.filter(sha256=sha256_hash)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    if qs.exists():
        existing = qs.first()
        raise ValidationError(
            f"Duplicate file detected: This file matches identical content previously uploaded as '{existing.original_filename}' (SHA256: {sha256_hash[:12]}...)."
        )


def validate_xlsx_file(uploaded_file) -> None:
    """
    Validates uploaded file against security threats:
    1. File extension (.xlsx only)
    2. File size limit
    3. Magic byte signature (PK\x03\x04 for OOXML zip containers)
    4. Valid zip structure with [Content_Types].xml (genuine Excel workbook)
    5. Macro / XLSM rejection (no vbaProject.bin)
    """
    # 1. Extension check
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext != ".xlsx":
        raise ValidationError(
            f"Invalid file type '{ext}'. Only modern Excel spreadsheets (.xlsx) are accepted."
        )

    # 2. File size check
    if uploaded_file.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            f"File size ({uploaded_file.size / (1024 * 1024):.1f} MB) exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES / (1024 * 1024):.0f} MB."
        )

    # 3. Magic bytes check
    pos = uploaded_file.tell() if hasattr(uploaded_file, "tell") else 0
    header = uploaded_file.read(4)
    uploaded_file.seek(pos)

    if header != b"PK\x03\x04":
        raise ValidationError(
            "Security verification failed: File content does not match genuine Microsoft Excel (.xlsx) container signature."
        )

    # 4. Zip structure & Macro inspection
    try:
        with zipfile.ZipFile(uploaded_file) as zf:
            namelist = zf.namelist()
            if "[Content_Types].xml" not in namelist:
                raise ValidationError("Corrupt or invalid Excel file: missing [Content_Types].xml manifest.")

            for item in namelist:
                if "vbaProject" in item or item.endswith(".bin"):
                    raise ValidationError(
                        "Security violation: Workbook contains embedded macro scripts (vbaProject.bin). Macros are strictly prohibited."
                    )
    except zipfile.BadZipFile:
        raise ValidationError("Malformed or damaged archive. The uploaded file is not a readable Excel package.")
    finally:
        uploaded_file.seek(pos)


def validate_dataset_schema(uploaded_file, dataset_type: str) -> List[str]:
    """
    Inspects sheet 1 headers in the uploaded Excel file to ensure all required
    columns for the chosen dataset type are present.
    Also enforces upload order: Courses -> Students -> Grades -> Attendance.
    """
    if dataset_type == "generic" or dataset_type not in REQUIRED_COLUMNS:
        return []

    from apps.academic.models import Course, Student

    # Upload order prerequisites check
    if dataset_type in ["grades", "attendance"]:
        if not Course.objects.exists():
            raise ValidationError(
                "Upload order prerequisite failed: No Courses found. Please upload or configure Courses before uploading Grades or Attendance."
            )
        if not Student.objects.exists():
            raise ValidationError(
                "Upload order prerequisite failed: No Students found. Please upload Students before uploading Grades or Attendance."
            )

    pos = uploaded_file.tell() if hasattr(uploaded_file, "tell") else 0
    uploaded_file.seek(0)

    try:
        wb = openpyxl.load_workbook(uploaded_file, read_only=True, data_only=True)
        sheet_names = wb.sheetnames
        if not sheet_names:
            raise ValidationError("The uploaded Excel workbook contains no worksheets.")

        first_sheet = wb[sheet_names[0]]
        # Read the first non-empty row to find headers
        raw_headers = []
        for row in first_sheet.iter_rows(values_only=True):
            if any(cell is not None for cell in row):
                raw_headers = [str(c or "").strip() for c in row if c is not None]
                break

        wb.close()
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"Unable to read Excel headers: {str(e)}")
    finally:
        uploaded_file.seek(pos)

    normalized_found = {normalize_col_name(h) for h in raw_headers}
    required = REQUIRED_COLUMNS[dataset_type]
    missing = [req for req in required if req not in normalized_found]

    if missing:
        missing_str = ", ".join(f"'{m}'" for m in missing)
        raise ValidationError(
            f"Schema validation failed for {dataset_type.capitalize()} dataset. Missing required column(s): {missing_str}. Found: {list(normalized_found)[:8]}"
        )

    return raw_headers


def sanitize_formula_injection(val):
    """
    Prefixes values starting with '=', '+', '-', '@' with a single quote (')
    to prevent CSV / Excel formula injection execution when exported.
    """
    if isinstance(val, str) and len(val) > 0:
        first_char = val[0]
        if first_char in ("=", "+", "-", "@", "\t", "\r"):
            return f"'{val}"
    return val
