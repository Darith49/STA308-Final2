"""
Core Data Cleaning Pipeline Orchestrator.
Sequences all cleaning rules, manages progress callbacks,
and outputs cleaned data and statistical quality reports.
Pure Python/pandas - NO Django imports.
"""

import os
from typing import Optional, Callable, Dict, Any, List, Tuple
from dataclasses import dataclass
import openpyxl
import pandas as pd
import numpy as np

from apps.cleaning.types import (
    CleaningConfig,
    CleaningActionItem,
    QualityReportData,
    Severity,
)
from apps.cleaning.rules.headers import detect_header_row, normalize_headers
from apps.cleaning.rules.whitespace_nulls import (
    drop_empty_rows_cols,
    trim_whitespace,
    unify_null_tokens,
)
from apps.cleaning.rules.types_coercion import coerce_numeric_columns
from apps.cleaning.rules.dates import parse_dates
from apps.cleaning.rules.duplicates import remove_exact_duplicates, detect_key_duplicates
from apps.cleaning.rules.categories import clean_categories
from apps.cleaning.rules.validation import (
    validate_ranges,
    detect_outliers,
    handle_missing_values,
    check_cross_column_consistency,
)
from apps.cleaning.profiling import generate_quality_report


@dataclass
class PipelineResult:
    """Contains full outputs of the cleaning pipeline."""
    clean_df: pd.DataFrame
    raw_df: pd.DataFrame
    report: QualityReportData
    actions: List[CleaningActionItem]
    sheet_names: List[str]
    header_mapping: Dict[str, str]
    current_sheet: str


class DataCleaningPipeline:
    """
    Executes end-to-end data cleaning workflow according to documented rules R01-R14.
    """

    def __init__(self, config: Optional[CleaningConfig] = None):
        self.config = config or CleaningConfig()

    def run_file(
        self,
        file_path_or_buffer: Any,
        sheet_name: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> PipelineResult:
        """Execute full cleaning pipeline on an XLSX file or buffer."""
        def update_progress(pct: int, msg: str):
            if progress_callback:
                progress_callback(pct, msg)

        # Stage 1: Ingest (0% - 10%)
        update_progress(5, "Ingesting Excel spreadsheet and inspecting sheets...")
        
        # Read available sheet names using openpyxl
        try:
            wb = openpyxl.load_workbook(file_path_or_buffer, read_only=True, data_only=True)
            sheet_names = wb.sheetnames
            target_sheet = sheet_name if (sheet_name and sheet_name in sheet_names) else sheet_names[0]
            wb.close()
        except Exception as e:
            # Fallback for csv or in-memory
            sheet_names = ["Sheet1"]
            target_sheet = "Sheet1"

        update_progress(10, f"Loading sheet '{target_sheet}' into memory...")
        # Read raw data with no header assumption initially
        try:
            raw_df = pd.read_excel(file_path_or_buffer, sheet_name=target_sheet, header=None)
        except Exception:
            # Try CSV fallback
            raw_df = pd.read_csv(file_path_or_buffer, header=None)

        all_actions: List[CleaningActionItem] = []

        # Stage 2: Structure & Header Row Detection (R01) (15%)
        update_progress(15, "Detecting table structure and header rows (R01)...")
        df_structured, header_row_idx, header_actions = detect_header_row(raw_df)
        all_actions.extend(header_actions)

        # Stage 3: Header Normalization (R02) (25%)
        update_progress(25, "Normalizing column headers to snake_case (R02)...")
        df_normalized, header_mapping, norm_actions = normalize_headers(df_structured)
        all_actions.extend(norm_actions)

        # Baseline reference dataframe with normalized headers for profile comparisons
        baseline_raw = df_normalized.copy()

        # Stage 4: Drop Empty Rows and Columns (R03) (35%)
        update_progress(35, "Removing empty rows and columns (R03)...")
        if self.config.drop_all_null_rows or self.config.drop_all_null_cols:
            df_no_empty, empty_actions = drop_empty_rows_cols(df_normalized)
            all_actions.extend(empty_actions)
        else:
            df_no_empty = df_normalized

        # Stage 5: Whitespace and Null Token Unification (R04, R05) (45%)
        update_progress(45, "Trimming whitespace and unifying missing tokens (R04, R05)...")
        df_trimmed, trim_actions = trim_whitespace(df_no_empty)
        all_actions.extend(trim_actions)

        df_nulls, null_actions = unify_null_tokens(df_trimmed)
        all_actions.extend(null_actions)

        # Stage 6: Numeric Type Coercion (R06) (55%)
        update_progress(55, "Inferring types and standardizing numeric fields (R06)...")
        df_coerced, inferred_types, num_actions = coerce_numeric_columns(df_nulls)
        all_actions.extend(num_actions)

        # Stage 7: Date Parsing (R07) (65%)
        update_progress(65, "Parsing mixed date formats and checking ambiguity (R07)...")
        df_dates, date_cols, date_actions = parse_dates(
            df_coerced,
            ambiguous_preference=self.config.ambiguous_date_preference
        )
        all_actions.extend(date_actions)

        # Stage 8: Duplicate Removal & Key Detection (R08, R13) (75%)
        update_progress(75, "Checking exact duplicate rows and semantic keys (R08, R13)...")
        if self.config.remove_exact_duplicates:
            df_dedup, dup_count, dup_actions = remove_exact_duplicates(df_dates)
            all_actions.extend(dup_actions)
        else:
            df_dedup = df_dates

        # Key duplicates (flag only)
        _, key_dup_count, key_actions = detect_key_duplicates(df_dedup, key_columns=self.config.key_columns)
        all_actions.extend(key_actions)

        # Stage 9: Categorical Typo Repair (R09) (82%)
        update_progress(82, "Repairing categorical misspellings via fuzzy matching (R09)...")
        df_cat, cat_actions = clean_categories(df_dedup, fuzzy_threshold=self.config.fuzzy_threshold)
        all_actions.extend(cat_actions)

        # Stage 10: Validation, Outliers, Missing & Consistency (R10, R11, R12, R14) (90%)
        update_progress(90, "Evaluating range validity, statistical outliers, and consistency (R10-R14)...")
        # R10: Range check
        _, range_actions = validate_ranges(df_cat, custom_ranges=self.config.custom_ranges)
        all_actions.extend(range_actions)

        # R11: Outlier detection
        outlier_counts, _, outlier_actions = detect_outliers(df_cat, method=self.config.outlier_method)
        all_actions.extend(outlier_actions)

        # R12: Missing handling
        df_missing, miss_actions = handle_missing_values(
            df_cat,
            numeric_strategy=self.config.missing_numeric_strategy,
            category_strategy=self.config.missing_category_strategy,
        )
        all_actions.extend(miss_actions)

        # R14: Cross-column consistency
        _, cross_actions = check_cross_column_consistency(df_missing)
        all_actions.extend(cross_actions)

        # Set sheet name on all action items
        for action in all_actions:
            action.sheet_name = target_sheet

        # Stage 11: Statistical Profiling & Quality Report (95%)
        update_progress(95, "Computing statistical profiles and composite quality score...")
        report = generate_quality_report(
            raw_df=baseline_raw,
            clean_df=df_missing,
            header_mapping=header_mapping,
            actions=all_actions,
            outlier_counts=outlier_counts,
        )

        update_progress(100, "Pipeline processing finished successfully!")

        return PipelineResult(
            clean_df=df_missing,
            raw_df=baseline_raw,
            report=report,
            actions=all_actions,
            sheet_names=sheet_names,
            header_mapping=header_mapping,
            current_sheet=target_sheet,
        )
