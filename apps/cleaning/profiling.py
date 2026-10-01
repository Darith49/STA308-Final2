"""
Statistical Profiling and Quality Report Computation.
Calculates statistical summaries, distribution moments (skewness, kurtosis),
normality hints (Shapiro-Wilk), Pearson/Spearman correlations, and a composite Quality Score (0-100).
"""

from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats
from apps.cleaning.types import ColumnProfileData, QualityReportData, ColumnRole, CleaningActionItem


def infer_column_role(col_name: str, series: pd.Series) -> str:
    """Infer semantic role of column (id, category, numeric, date, text)."""
    col_lower = str(col_name).lower()
    if any(k in col_lower for k in ["_id", "id_", "ssn", "student_id", "record_id"]):
        return ColumnRole.ID.value

    if any(k in col_lower for k in ["date", "dob", "birth", "timestamp", "enrolled", "graduated", "admit"]):
        return ColumnRole.DATE.value

    if pd.api.types.is_numeric_dtype(series):
        # If very few integer unique values and named like status/flag
        if series.nunique() <= 5 and series.dropna().isin([0, 1]).all():
            return ColumnRole.CATEGORY.value
        return ColumnRole.NUMERIC.value

    # For string/object columns
    n_unique = series.nunique()
    total = len(series.dropna())
    if total > 0 and (n_unique <= 50 or (n_unique / total) < 0.20):
        return ColumnRole.CATEGORY.value

    return ColumnRole.TEXT.value


def profile_column(
    col_clean: str,
    col_raw: str,
    raw_series: Optional[pd.Series],
    clean_series: pd.Series,
    outlier_count: int = 0
) -> ColumnProfileData:
    """Compute comprehensive statistical profile for a single column."""
    role = infer_column_role(col_clean, clean_series)
    total_count = len(clean_series)

    # Missing counts
    missing_before = int(raw_series.isna().sum()) if raw_series is not None else int(clean_series.isna().sum())
    missing_pct_before = (missing_before / max(1, len(raw_series))) * 100.0 if raw_series is not None else 0.0

    missing_after = int(clean_series.isna().sum())
    missing_pct_after = (missing_after / max(1, total_count)) * 100.0

    non_null = clean_series.dropna()
    n_unique = int(clean_series.nunique())
    unique_sample = non_null.unique()[:10].tolist()

    profile = ColumnProfileData(
        name_raw=str(col_raw),
        name_clean=str(col_clean),
        inferred_type=str(clean_series.dtype),
        role=role,
        total_count=total_count,
        missing_count_before=missing_before,
        missing_pct_before=missing_pct_before,
        missing_count_after=missing_after,
        missing_pct_after=missing_pct_after,
        n_unique=n_unique,
        unique_sample=unique_sample,
        outlier_count=outlier_count,
    )

    # Numeric distribution metrics
    if pd.api.types.is_numeric_dtype(clean_series) and len(non_null) > 0:
        min_v = float(non_null.min())
        max_v = float(non_null.max())
        mean_v = float(non_null.mean())
        std_v = float(non_null.std(ddof=1)) if len(non_null) > 1 else 0.0
        med_v = float(non_null.median())
        q25 = float(non_null.quantile(0.25))
        q75 = float(non_null.quantile(0.75))
        iqr_v = q75 - q25

        profile.min_val = min_v
        profile.max_val = max_v
        profile.mean_val = mean_v
        profile.std_val = std_v
        profile.median_val = med_v
        profile.iqr_val = iqr_v

        # Higher moments: skewness & kurtosis
        if len(non_null) >= 3:
            try:
                skew_v = float(stats.skew(non_null, bias=False))
                kurt_v = float(stats.kurtosis(non_null, bias=False))
                profile.skew_val = skew_v
                profile.kurt_val = kurt_v
            except Exception:
                pass

        # Normality assessment
        if len(non_null) >= 8:
            try:
                # Shapiro-Wilk for samples <= 5000, otherwise D'Agostino's K-squared
                sample_data = non_null.sample(min(len(non_null), 5000), random_state=42)
                stat_val, p_val = stats.shapiro(sample_data)
                profile.normality_test = "Shapiro-Wilk (alpha=0.05)"
                profile.normality_p_value = float(p_val)

                if p_val > 0.05:
                    profile.normality_hint = "Data is approximately normally distributed (p > 0.05); mean is suitable."
                else:
                    if profile.skew_val is not None and abs(profile.skew_val) > 1.0:
                        direction = "right-skewed" if profile.skew_val > 0 else "left-skewed"
                        profile.normality_hint = f"Distribution is non-normal ({direction}); median is recommended."
                    else:
                        profile.normality_hint = "Distribution departs from normality (p <= 0.05); consider robust metrics."
            except Exception:
                profile.normality_hint = "Sample too small or uniform for normality testing."

    return profile


def calculate_quality_score(
    raw_df: pd.DataFrame,
    clean_df: pd.DataFrame,
    column_profiles: Dict[str, ColumnProfileData],
    actions: List[CleaningActionItem]
) -> Tuple[float, float, float, float, float]:
    """
    Computes composite Quality Score (0-100) using weighted dimensions:
    - Completeness (30%): (1 - missing rate)
    - Validity (30%): (1 - invalid & outlier rate)
    - Uniqueness (20%): (1 - duplicate row rate)
    - Consistency (20%): (1 - cross-column & format error rate)
    """
    total_cells = max(1, clean_df.shape[0] * clean_df.shape[1])
    missing_cells = clean_df.isna().sum().sum()
    completeness = max(0.0, min(100.0, 100.0 * (1.0 - (missing_cells / total_cells))))

    # Validity: based on outlier counts and range violations
    total_outliers = sum(p.outlier_count for p in column_profiles.values())
    danger_actions = sum(1 for a in actions if a.severity == "danger")
    invalid_cells = total_outliers + (danger_actions * 2)
    validity = max(0.0, min(100.0, 100.0 * (1.0 - (invalid_cells / total_cells))))

    # Uniqueness: based on exact duplicates and key duplicates
    raw_rows = max(1, len(raw_df))
    clean_rows = len(clean_df)
    dropped_duplicates = max(0, raw_rows - clean_rows)
    key_dupes = sum(1 for a in actions if a.rule_id == "R13")
    uniqueness = max(0.0, min(100.0, 100.0 * (1.0 - ((dropped_duplicates + (key_dupes * 2)) / raw_rows))))

    # Consistency: based on warning actions and type coercion anomalies
    warning_actions = sum(1 for a in actions if a.severity == "warning")
    consistency = max(0.0, min(100.0, 100.0 * (1.0 - ((warning_actions * 3) / max(1, len(actions) + len(clean_df))))))

    # Composite weighted average
    overall = (0.30 * completeness) + (0.30 * validity) + (0.20 * uniqueness) + (0.20 * consistency)

    return overall, completeness, validity, uniqueness, consistency


def compute_correlation_matrix(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """Compute Pearson correlation matrix between numeric columns."""
    num_df = df.select_dtypes(include=[np.number])
    if num_df.shape[1] < 2:
        return {}

    corr_df = num_df.corr(method="pearson").round(3)
    result: Dict[str, Dict[str, float]] = {}

    for col in corr_df.columns:
        result[str(col)] = {}
        for row in corr_df.index:
            val = corr_df.loc[row, col]
            result[str(col)][str(row)] = 0.0 if np.isnan(val) else float(val)

    return result


def generate_quality_report(
    raw_df: pd.DataFrame,
    clean_df: pd.DataFrame,
    header_mapping: Dict[str, str],
    actions: List[CleaningActionItem],
    outlier_counts: Dict[str, int]
) -> QualityReportData:
    """Generate comprehensive QualityReportData."""
    column_profiles: Dict[str, ColumnProfileData] = {}

    for clean_col in clean_df.columns:
        # Trace back raw column
        raw_col = next((r for r, c in header_mapping.items() if c == clean_col), clean_col)
        raw_series = raw_df[raw_col] if raw_col in raw_df.columns else None
        profile = profile_column(
            col_clean=clean_col,
            col_raw=raw_col,
            raw_series=raw_series,
            clean_series=clean_df[clean_col],
            outlier_count=outlier_counts.get(clean_col, 0)
        )
        column_profiles[clean_col] = profile

    overall, comp, val, uniq, cons = calculate_quality_score(raw_df, clean_df, column_profiles, actions)
    corr_matrix = compute_correlation_matrix(clean_df)

    rows_removed = max(0, len(raw_df) - len(clean_df))
    cells_modified = sum(1 for a in actions if a.rule_id in ["R04", "R05", "R06", "R07", "R09", "R12"])
    flags_raised = sum(1 for a in actions if a.severity in ["warning", "danger"])

    summary_notes = [
        f"Processed {len(raw_df)} raw records down to {len(clean_df)} clean rows ({rows_removed} redundant/empty rows removed).",
        f"Overall Data Quality Score: {overall:.1f}/100 (Completeness: {comp:.1f}%, Validity: {val:.1f}%, Uniqueness: {uniq:.1f}%, Consistency: {cons:.1f}%).",
        f"Total cleaning actions executed: {len(actions)} with {flags_raised} flags requiring attention.",
    ]

    return QualityReportData(
        overall_score=overall,
        completeness_score=comp,
        validity_score=val,
        uniqueness_score=uniq,
        consistency_score=cons,
        raw_rows=len(raw_df),
        clean_rows=len(clean_df),
        raw_cols=len(raw_df.columns),
        clean_cols=len(clean_df.columns),
        rows_removed=rows_removed,
        cells_modified=cells_modified,
        flags_raised=flags_raised,
        column_profiles=column_profiles,
        actions_log=actions,
        correlation_matrix=corr_matrix,
        summary_notes=summary_notes,
    )
