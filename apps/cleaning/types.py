"""
Pure-Python Type Definitions and Dataclasses for Data Cleaning Pipeline.
Contains NO Django imports so that it can be unit-tested independently
and easily imported across scientific scripts and pipelines.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"


class ColumnRole(str, Enum):
    ID = "id"
    CATEGORY = "category"
    NUMERIC = "numeric"
    DATE = "date"
    TEXT = "text"


@dataclass
class CleaningConfig:
    """Configurable options per upload cleaning run."""
    fuzzy_threshold: float = 85.0
    outlier_method: str = "iqr"  # 'iqr' or 'zscore'
    outlier_action: str = "flag"  # 'flag' or 'clip'
    missing_numeric_strategy: str = "flag"  # 'flag' or 'median' or 'mean'
    missing_category_strategy: str = "flag"  # 'flag' or 'unknown'
    ambiguous_date_preference: str = "DMY"  # 'DMY' or 'MDY'
    min_category_ratio: float = 0.85
    drop_all_null_rows: bool = True
    drop_all_null_cols: bool = True
    remove_exact_duplicates: bool = True
    key_columns: List[str] = field(default_factory=list)
    custom_ranges: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # e.g. {'grade': {'min': 0, 'max': 100}, 'age': {'min': 15, 'max': 100}}


@dataclass
class CleaningActionItem:
    """Represents a discrete action or modification taken by a rule."""
    rule_id: str
    rule_name: str
    sheet_name: str = "Sheet1"
    column: str = ""
    row_ref: Optional[int] = None
    before_value: Optional[str] = None
    after_value: Optional[str] = None
    reason: str = ""
    severity: str = Severity.INFO.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "sheet_name": self.sheet_name,
            "column": self.column,
            "row_ref": self.row_ref,
            "before_value": self.before_value,
            "after_value": self.after_value,
            "reason": self.reason,
            "severity": self.severity,
        }


@dataclass
class ColumnProfileData:
    """Detailed statistical profile for a single column."""
    name_raw: str
    name_clean: str
    inferred_type: str
    role: str
    total_count: int = 0
    missing_count_before: int = 0
    missing_pct_before: float = 0.0
    missing_count_after: int = 0
    missing_pct_after: float = 0.0
    n_unique: int = 0
    unique_sample: List[Any] = field(default_factory=list)
    # Numeric summary statistics
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    mean_val: Optional[float] = None
    std_val: Optional[float] = None
    median_val: Optional[float] = None
    iqr_val: Optional[float] = None
    skew_val: Optional[float] = None
    kurt_val: Optional[float] = None
    outlier_count: int = 0
    # Normality assessment
    normality_test: str = ""
    normality_p_value: Optional[float] = None
    normality_hint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name_raw": self.name_raw,
            "name_clean": self.name_clean,
            "inferred_type": self.inferred_type,
            "role": self.role,
            "total_count": self.total_count,
            "missing_count_before": self.missing_count_before,
            "missing_pct_before": round(self.missing_pct_before, 2),
            "missing_count_after": self.missing_count_after,
            "missing_pct_after": round(self.missing_pct_after, 2),
            "n_unique": self.n_unique,
            "unique_sample": self.unique_sample[:10],
            "min_val": round(self.min_val, 2) if self.min_val is not None else None,
            "max_val": round(self.max_val, 2) if self.max_val is not None else None,
            "mean_val": round(self.mean_val, 2) if self.mean_val is not None else None,
            "std_val": round(self.std_val, 2) if self.std_val is not None else None,
            "median_val": round(self.median_val, 2) if self.median_val is not None else None,
            "iqr_val": round(self.iqr_val, 2) if self.iqr_val is not None else None,
            "skew_val": round(self.skew_val, 2) if self.skew_val is not None else None,
            "kurt_val": round(self.kurt_val, 2) if self.kurt_val is not None else None,
            "outlier_count": self.outlier_count,
            "normality_test": self.normality_test,
            "normality_p_value": round(self.normality_p_value, 4) if self.normality_p_value is not None else None,
            "normality_hint": self.normality_hint,
        }


@dataclass
class QualityReportData:
    """Complete summary of data quality metrics and score."""
    overall_score: float = 0.0
    completeness_score: float = 0.0
    validity_score: float = 0.0
    uniqueness_score: float = 0.0
    consistency_score: float = 0.0
    raw_rows: int = 0
    clean_rows: int = 0
    raw_cols: int = 0
    clean_cols: int = 0
    rows_removed: int = 0
    cells_modified: int = 0
    flags_raised: int = 0
    column_profiles: Dict[str, ColumnProfileData] = field(default_factory=dict)
    actions_log: List[CleaningActionItem] = field(default_factory=list)
    correlation_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    formula_weights: Dict[str, float] = field(default_factory=lambda: {
        "completeness": 0.30,
        "validity": 0.30,
        "uniqueness": 0.20,
        "consistency": 0.20
    })
    summary_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 1),
            "completeness_score": round(self.completeness_score, 1),
            "validity_score": round(self.validity_score, 1),
            "uniqueness_score": round(self.uniqueness_score, 1),
            "consistency_score": round(self.consistency_score, 1),
            "raw_rows": self.raw_rows,
            "clean_rows": self.clean_rows,
            "raw_cols": self.raw_cols,
            "clean_cols": self.clean_cols,
            "rows_removed": self.rows_removed,
            "cells_modified": self.cells_modified,
            "flags_raised": self.flags_raised,
            "formula_weights": self.formula_weights,
            "summary_notes": self.summary_notes,
            "column_profiles": {k: v.to_dict() for k, v in self.column_profiles.items()},
            "actions_log": [a.to_dict() for a in self.actions_log],
            "correlation_matrix": self.correlation_matrix,
        }
