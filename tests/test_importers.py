import os
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from uploads.models import Upload, UploadStatus, UploadError
from academics.models import Student
from services.importers import run_import_pipeline, generate_error_xlsx
from services.templates_xlsx import generate_template_xlsx

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sample_data')

@pytest.mark.django_db
def test_import_clean_students_file(admin_user):
    file_path = os.path.join(SAMPLE_DIR, 'students_clean.xlsx')
    assert os.path.exists(file_path), "Sample file students_clean.xlsx not found"

    with open(file_path, 'rb') as f:
        up_file = SimpleUploadedFile('students_clean.xlsx', f.read())

    upload = Upload.objects.create(
        file=up_file,
        original_filename='students_clean.xlsx',
        file_hash='fakehashclean123',
        dataset_type='students',
        uploaded_by=admin_user,
    )

    processed_upload = run_import_pipeline(upload.id)
    assert processed_upload.status == UploadStatus.DONE
    assert processed_upload.rows_ok > 0
    assert processed_upload.rows_rejected == 0
    assert Student.objects.filter(upload=processed_upload).count() == processed_upload.rows_ok

@pytest.mark.django_db
def test_import_messy_students_file_reports_errors(admin_user):
    file_path = os.path.join(SAMPLE_DIR, 'students_messy.xlsx')
    assert os.path.exists(file_path), "Sample file students_messy.xlsx not found"

    with open(file_path, 'rb') as f:
        up_file = SimpleUploadedFile('students_messy.xlsx', f.read())

    upload = Upload.objects.create(
        file=up_file,
        original_filename='students_messy.xlsx',
        file_hash='fakehashmessy123',
        dataset_type='students',
        uploaded_by=admin_user,
    )

    processed_upload = run_import_pipeline(upload.id)
    assert processed_upload.status == UploadStatus.DONE
    assert processed_upload.rows_rejected > 0
    assert processed_upload.errors.count() > 0

    # Test error file export
    err_bytes = generate_error_xlsx(processed_upload)
    assert len(err_bytes) > 0

@pytest.mark.django_db
def test_cascade_delete_rollback(admin_user):
    file_path = os.path.join(SAMPLE_DIR, 'students_clean.xlsx')
    with open(file_path, 'rb') as f:
        up_file = SimpleUploadedFile('students_clean.xlsx', f.read())

    upload = Upload.objects.create(
        file=up_file,
        original_filename='students_clean.xlsx',
        file_hash='fakehashrollback',
        dataset_type='students',
        uploaded_by=admin_user,
    )

    processed_upload = run_import_pipeline(upload.id)
    imported_count = Student.objects.filter(upload=processed_upload).count()
    assert imported_count > 0

    # Delete upload
    processed_upload.delete()
    # Verify all imported rows were cascadingly deleted
    assert Student.objects.filter(upload_id=upload.id).count() == 0

def test_template_generator():
    for dt in ['students', 'courses', 'grades', 'attendance']:
        data = generate_template_xlsx(dt)
        assert len(data) > 0
        assert data.startswith(b'PK')  # Standard zip/xlsx file magic signature
