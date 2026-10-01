"""
Security and Integration Tests for Django Portal:
- Formula Injection Prevention
- File Type & Magic Byte Validation
- User Data Isolation (O6)
- REST API Aggregation Endpoints
"""

import os
import io
import json
import zipfile
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from apps.uploads.models import Upload, UploadStatus
from apps.uploads.validators import validate_xlsx_file, sanitize_formula_injection
from apps.dashboards.aggregation import load_cleaned_dataframe


class SecurityAndIsolationTests(TestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(username="prof_smith", password="password123")
        self.user2 = User.objects.create_user(username="prof_jones", password="password123")

        self.client1 = Client()
        self.client1.login(username="prof_smith", password="password123")

        self.client2 = Client()
        self.client2.login(username="prof_jones", password="password123")

        # Create dummy upload for user1
        self.upload1 = Upload.objects.create(
            owner=self.user1,
            original_filename="grades_fall.xlsx",
            status=UploadStatus.DONE,
            row_count_raw=100,
            row_count_clean=95,
            quality_score=92.5,
        )

    def test_formula_injection_sanitization(self):
        """Formula injection protection: cells starting with = + - @ are prefixed with '."""
        dangerous_inputs = [
            "=SUM(A1:A10)",
            "+cmd|' /C calc'!A0",
            "-2+3*cmd|' /C notepad'!A0",
            "@SUM(1,2)",
            "\t=CMD()",
        ]
        for val in dangerous_inputs:
            sanitized = sanitize_formula_injection(val)
            self.assertTrue(sanitized.startswith("'"), f"Failed for input: {val}")

        # Safe input should remain unchanged
        self.assertEqual(sanitize_formula_injection("Normal Student Name"), "Normal Student Name")
        self.assertEqual(sanitize_formula_injection(85.5), 85.5)

    def test_reject_non_xlsx_extension(self):
        """Reject non-xlsx file extensions."""
        fake_csv = SimpleUploadedFile("grades.csv", b"student_id,grade\n1,100", content_type="text/csv")
        with self.assertRaises(ValidationError):
            validate_xlsx_file(fake_csv)

    def test_reject_fake_xlsx_magic_bytes(self):
        """Reject file named .xlsx that does not have ZIP magic bytes PK\\x03\\x04."""
        fake_exe = SimpleUploadedFile("trojan.xlsx", b"MZ\x90\x00\x03\x00\x00\x00", content_type="application/octet-stream")
        with self.assertRaises(ValidationError):
            validate_xlsx_file(fake_exe)

    def test_user_data_isolation_report_view(self):
        """O6: User 2 should NOT be able to view User 1's report (returns 404)."""
        response_user1 = self.client1.get(f"/uploads/{self.upload1.id}/report/")
        self.assertEqual(response_user1.status_code, 200)

        response_user2 = self.client2.get(f"/uploads/{self.upload1.id}/report/")
        self.assertEqual(response_user2.status_code, 404)

    def test_user_data_isolation_api(self):
        """O6: User 2 should NOT be able to access User 1's status or chart data API."""
        status_url = f"/api/uploads/{self.upload1.id}/status/"
        
        # User 1 succeeds
        res1 = self.client1.get(status_url)
        self.assertEqual(res1.status_code, 200)

        # User 2 receives 404
        res2 = self.client2.get(status_url)
        self.assertEqual(res2.status_code, 404)
