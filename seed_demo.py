"""
Seed script to create a demo user and initial sample uploads.
Usage: python seed_demo.py
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User
from django.core.files import File
from apps.accounts.models import UserProfile, UserRole
from apps.uploads.models import Upload, UploadStatus
from apps.uploads.tasks import run_pipeline_for_upload

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "tests", "fixtures")


def seed():
    print("Seeding demo account and sample datasets...")
    username = "demo_analyst"
    password = "password123"

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": "analyst@university.edu",
            "first_name": "Alex",
            "last_name": "Taylor",
        },
    )
    user.set_password(password)
    user.save()

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.role = UserRole.DATA_ANALYST
    profile.department = "Department of Statistics & Data Science"
    profile.save()

    print(f"-> Demo User Ready: username='{username}', password='{password}'")

    # Sample file 1: messy_headers.xlsx
    messy_file = os.path.join(FIXTURES_DIR, "messy_headers.xlsx")
    if os.path.exists(messy_file) and not Upload.objects.filter(owner=user, original_filename="messy_headers.xlsx").exists():
        with open(messy_file, "rb") as f:
            upload_rec = Upload.objects.create(
                owner=user,
                original_filename="messy_headers.xlsx",
                stored_file=File(f, name="messy_headers.xlsx"),
                size_bytes=os.path.getsize(messy_file),
                status=UploadStatus.QUEUED,
                config_options={
                    "fuzzy_threshold": 85,
                    "outlier_method": "iqr",
                    "missing_numeric_strategy": "flag",
                    "missing_category_strategy": "flag",
                    "ambiguous_date_preference": "DMY",
                },
            )
            print(f"-> Created Upload: {upload_rec.id} (messy_headers.xlsx). Processing...")
            run_pipeline_for_upload(str(upload_rec.id))
            upload_rec.refresh_from_db()
            print(f"-> Finished processing {upload_rec.id}! Quality Score: {upload_rec.quality_score:.1f}")

    # Sample file 2: clean_baseline.xlsx
    clean_file = os.path.join(FIXTURES_DIR, "clean_baseline.xlsx")
    if os.path.exists(clean_file) and not Upload.objects.filter(owner=user, original_filename="clean_baseline.xlsx").exists():
        with open(clean_file, "rb") as f:
            upload_rec2 = Upload.objects.create(
                owner=user,
                original_filename="clean_baseline.xlsx",
                stored_file=File(f, name="clean_baseline.xlsx"),
                size_bytes=os.path.getsize(clean_file),
                status=UploadStatus.QUEUED,
                config_options={"fuzzy_threshold": 85, "outlier_method": "iqr"},
            )
            print(f"-> Created Upload: {upload_rec2.id} (clean_baseline.xlsx). Processing...")
            run_pipeline_for_upload(str(upload_rec2.id))
            upload_rec2.refresh_from_db()
            print(f"-> Finished processing {upload_rec2.id}! Quality Score: {upload_rec2.quality_score:.1f}")

    print("\nSeed completed successfully!")


if __name__ == "__main__":
    seed()
