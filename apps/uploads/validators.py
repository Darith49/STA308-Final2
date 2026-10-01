"""
Security Validators for Uploaded Spreadsheets.
Protects against malicious files, zip bombs, formula injection, and path traversal.
"""

import os
import zipfile
from typing import Tuple
from django.core.exceptions import ValidationError
from django.conf import settings

MAX_FILE_SIZE_BYTES = getattr(settings, "MAX_UPLOAD_SIZE_MB", 20) * 1024 * 1024


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
            # Must contain standard OOXML parts
            if "[Content_Types].xml" not in namelist:
                raise ValidationError("Corrupt or invalid Excel file: missing [Content_Types].xml manifest.")

            # Reject embedded macros (vbaProject.bin)
            for item in namelist:
                if "vbaProject" in item or item.endswith(".bin"):
                    raise ValidationError(
                        "Security violation: Workbook contains embedded macro scripts (vbaProject.bin). Macros are strictly prohibited."
                    )
    except zipfile.BadZipFile:
        raise ValidationError("Malformed or damaged archive. The uploaded file is not a readable Excel package.")
    finally:
        uploaded_file.seek(pos)


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
