"""
Unit tests for pure Python cleaning pipeline (R01 - R14).
Runs independently without Django.
"""

import unittest
import numpy as np
import pandas as pd
from apps.cleaning.pipeline import DataCleaningPipeline
from apps.cleaning.types import CleaningConfig
from apps.cleaning.rules.headers import detect_header_row, normalize_headers
from apps.cleaning.rules.whitespace_nulls import drop_empty_rows_cols, trim_whitespace, unify_null_tokens
from apps.cleaning.rules.types_coercion import coerce_numeric_columns
from apps.cleaning.rules.duplicates import remove_exact_duplicates, detect_key_duplicates
from apps.cleaning.rules.validation import detect_outliers, validate_ranges


class TestCleaningRules(unittest.TestCase):

    def test_r01_header_detection_and_summary_row_removal(self):
        """R01: Should skip title metadata and trailing totals."""
        data = [
            ["University Report Title", None, None],
            ["Confidential Export", None, None],
            ["student_id", "score", "grade"],
            ["S1", 85, "A"],
            ["S2", 90, "A"],
            ["Grand Total", 175, ""],
        ]
        df = pd.DataFrame(data)
        clean_df, header_row, actions = detect_header_row(df)
        self.assertEqual(header_row, 2)
        self.assertEqual(list(clean_df.columns), ["student_id", "score", "grade"])
        self.assertEqual(len(clean_df), 2)  # Trailing total dropped

    def test_r02_header_normalization(self):
        """R02: Headers converted to clean snake_case and deduplicated."""
        df = pd.DataFrame([[1, 2, 3, 4]], columns=["First Name ", "Exam / Score %", "First Name ", ""])
        clean_df, mapping, actions = normalize_headers(df)
        cols = list(clean_df.columns)
        self.assertEqual(cols[0], "first_name")
        self.assertEqual(cols[1], "exam_score")
        self.assertEqual(cols[2], "first_name_2")
        self.assertEqual(cols[3], "column_4")

    def test_r04_r05_whitespace_and_null_tokens(self):
        """R04, R05: Strip whitespace and convert null tokens to NaN."""
        df = pd.DataFrame({
            "dept": ["  Computer Science  ", "Mathematics", " N/A "],
            "status": ["-", "Enrolled", "null"]
        })
        df, _ = trim_whitespace(df)
        self.assertEqual(df.loc[0, "dept"], "Computer Science")

        df, _ = unify_null_tokens(df)
        self.assertTrue(pd.isna(df.loc[2, "dept"]))
        self.assertTrue(pd.isna(df.loc[0, "status"]))
        self.assertTrue(pd.isna(df.loc[2, "status"]))

    def test_r06_numeric_coercion(self):
        """R06: Sanitize currency, commas, and percentage strings."""
        df = pd.DataFrame({
            "tuition": ["$1,250.00", "$2,000", "$500.50"],
            "attendance": ["85%", "92.5%", "100%"],
            "notes": ["ok", "pending", "done"],
        })
        clean_df, inferred, actions = coerce_numeric_columns(df)
        self.assertEqual(inferred["tuition"], "float")
        self.assertEqual(clean_df.loc[0, "tuition"], 1250.0)
        self.assertEqual(clean_df.loc[0, "attendance"], 85.0)

    def test_r08_exact_duplicates(self):
        """R08: Exact duplicate rows removed, keeping first."""
        df = pd.DataFrame({
            "id": ["A", "B", "A", "C"],
            "val": [1, 2, 1, 3]
        })
        clean_df, count, actions = remove_exact_duplicates(df)
        self.assertEqual(count, 1)
        self.assertEqual(len(clean_df), 3)

    def test_r10_r11_range_and_outliers(self):
        """R10, R11: Range violation and Tukey's IQR detection."""
        # 20 points centered around 50 with extreme outliers 500, -50
        vals = [50 + i for i in range(20)] + [500.0, -50.0]
        df = pd.DataFrame({"score": vals})
        counts, bounds, actions = detect_outliers(df, method="iqr")
        self.assertGreater(counts.get("score", 0), 0)

        # Range validation
        _, r_actions = validate_ranges(df)
        self.assertTrue(any(a.rule_id == "R10" for a in r_actions))

    def test_idempotency(self):
        """Property: Cleaning an already clean DataFrame produces 0 structural alterations."""
        df = pd.DataFrame({
            "student_id": ["STU1", "STU2", "STU3"],
            "department": ["Computer Science", "Mathematics", "Physics"],
            "gpa": [3.5, 3.8, 3.2],
        })
        pipeline = DataCleaningPipeline()
        # Save temp file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            temp_path = f.name
            df.to_excel(temp_path, index=False)

        res1 = pipeline.run_file(temp_path)
        # Re-save cleaned
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f2:
            temp_path2 = f2.name
            res1.clean_df.to_excel(temp_path2, index=False)

        res2 = pipeline.run_file(temp_path2)
        # Idempotence: clean rows should match
        self.assertEqual(len(res1.clean_df), len(res2.clean_df))
        self.assertEqual(list(res1.clean_df.columns), list(res2.clean_df.columns))


if __name__ == "__main__":
    unittest.main()
