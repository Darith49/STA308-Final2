import hashlib
import os
from django.core.exceptions import ValidationError
from django.conf import settings
import openpyxl

MAX_UPLOAD_SIZE = getattr(settings, 'MAX_UPLOAD_SIZE', 5 * 1024 * 1024)  # 5MB
MAX_CELL_COUNT = getattr(settings, 'MAX_CELL_COUNT', 50000)

def compute_file_hash(file_obj):
    """Compute sha256 hash of a file-like object."""
    hasher = hashlib.sha256()
    pos = file_obj.tell()
    file_obj.seek(0)
    for chunk in file_obj.chunks(4096) if hasattr(file_obj, 'chunks') else iter(lambda: file_obj.read(4096), b''):
        hasher.update(chunk)
    file_obj.seek(pos)
    return hasher.hexdigest()

def validate_excel_file(file_obj):
    """
    Validate that an uploaded file is a safe, valid XLSX file:
    - Extension must be .xlsx
    - File size <= 5MB
    - Can be opened by openpyxl in read_only mode
    - Contains at least 1 sheet and not exceeding cell limits
    """
    filename = getattr(file_obj, 'name', '')
    ext = os.path.splitext(filename)[1].lower()
    if ext != '.xlsx':
        raise ValidationError(f"Invalid file extension '{ext}'. Only .xlsx files are permitted (macro-enabled .xlsm files are prohibited).")

    # Check size
    if file_obj.size > MAX_UPLOAD_SIZE:
        size_mb = file_obj.size / (1024 * 1024)
        raise ValidationError(f"File size ({size_mb:.2f} MB) exceeds maximum allowed limit of 5 MB.")

    # Validate openpyxl read_only opening
    try:
        wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
        if not wb.sheetnames:
            raise ValidationError("Excel workbook does not contain any sheets.")
        
        sheet = wb.active
        # Inspect dimensions
        max_rows = sheet.max_row or 0
        max_cols = sheet.max_column or 0
        if max_rows and max_cols and (max_rows * max_cols > MAX_CELL_COUNT):
            raise ValidationError(f"File exceeds cell limit (max {MAX_CELL_COUNT} cells allowed).")
        
        wb.close()
    except Exception as e:
        if isinstance(e, ValidationError):
            raise e
        raise ValidationError(f"Failed to open Excel file. Please ensure it is a valid, uncorrupted .xlsx workbook: {str(e)}")
    finally:
        file_obj.seek(0)
