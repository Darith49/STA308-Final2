"""
Rules R10, R11, R12, R14:
Range Validation, Outlier Detection, Missing-Value Handling, and Cross-Column Consistency.
"""

from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import pandas as pd
from apps.cleaning.types import CleaningActionItem, Severity


# Common domain ranges for academic and university datasets
DEFAULT_DOMAIN_RANGES = {
    "grade": (0.0, 100.0),
    "score": (0.0, 100.0),
    "exam_score": (0.0, 100.0),
    "final_grade": (0.0, 100.0),
    "gpa": (0.0, 4.0),
    "cgpa": (0.0, 4.0),
    "age": (15.0, 100.0),
    "credits": (0.0, 250.0),
    "credits_earned": (0.0, 250.0),
    "semester": (1.0, 12.0),
    "attendance_rate": (0.0, 100.0),
}


def validate_ranges(
    df: pd.DataFrame, custom_ranges: Optional[Dict[str, Dict[str, float]]] = None
) -> Tuple[pd.DataFrame, List[CleaningActionItem]]:
    """
    R10: Validate expected domain ranges (e.g., Grade 0-100, GPA 0-4, Age 15-100).
    Flags invalid entries without silent deletion.
    """
    actions: List[CleaningActionItem] = []
    ranges = DEFAULT_DOMAIN_RANGES.copy()

    if custom_ranges:
        for col_name, limits in custom_ranges.items():
            if "min" in limits and "max" in limits:
                ranges[col_name.lower()] = (float(limits["min"]), float(limits["max"]))

    for col in df.columns:
        col_lower = str(col).lower()
        matched_range = None
        for pattern, limits in ranges.items():
            if pattern == col_lower or (f"_{pattern}" in col_lower or f"{pattern}_" in col_lower):
                matched_range = limits
                break

        if matched_range and pd.api.types.is_numeric_dtype(df[col]):
            min_lim, max_lim = matched_range
            series = df[col].dropna()
            invalid_mask = (series < min_lim) | (series > max_lim)
            invalid_count = invalid_mask.sum()

            if invalid_count > 0:
                sample_invalid = series[invalid_mask].tolist()[:5]
                actions.append(
                    CleaningActionItem(
                        rule_id="R10",
                        rule_name="Domain Range Violation",
                        column=str(col),
                        before_value=f"{invalid_count} values outside [{min_lim}, {max_lim}]: {sample_invalid}",
                        after_value="Flagged in Quality Report (retained)",
                        reason=(
                            f"Detected {invalid_count} values outside expected domain range [{min_lim}, {max_lim}] "
                            f"in column '{col}'. Values retained per data integrity principle."
                        ),
                        severity=Severity.DANGER.value,
                    )
                )

    return df, actions


def detect_outliers(
    df: pd.DataFrame, method: str = "iqr"
) -> Tuple[Dict[str, int], Dict[str, List[float]], List[CleaningActionItem]]:
    """
    R11: Statistical Outlier Flagging using Tukey's IQR or Modified Z-Score (MAD).
    Returns (outlier_counts, outlier_bounds, actions).
    Flags only; never silently deletes.
    """
    actions: List[CleaningActionItem] = []
    outlier_counts: Dict[str, int] = {}
    bounds_dict: Dict[str, List[float]] = {}

    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue

        series = df[col].dropna()
        if len(series) < 10:  # Need minimum sample for statistical outlier detection
            continue

        col_str = str(col)

        if method == "zscore":
            # Boris Iglewicz & David Hoaglin Modified Z-score using Median & MAD
            median = series.median()
            mad = np.median(np.abs(series - median))
            if mad == 0:
                mad = np.mean(np.abs(series - median))

            if mad > 0:
                mod_z = 0.6745 * np.abs(series - median) / mad
                outliers = series[mod_z > 3.5]
                count = len(outliers)
                outlier_counts[col_str] = count
                bounds_dict[col_str] = [float(median - (3.5 * mad / 0.6745)), float(median + (3.5 * mad / 0.6745))]
            else:
                outlier_counts[col_str] = 0
        else:
            # Tukey's 1.5 * IQR rule
            q25 = float(series.quantile(0.25))
            q75 = float(series.quantile(0.75))
            iqr = q75 - q25
            lower_bound = q25 - 1.5 * iqr
            upper_bound = q75 + 1.5 * iqr
            bounds_dict[col_str] = [lower_bound, upper_bound]

            outliers = series[(series < lower_bound) | (series > upper_bound)]
            count = len(outliers)
            outlier_counts[col_str] = count

        if outlier_counts.get(col_str, 0) > 0:
            count = outlier_counts[col_str]
            sample = outliers.head(5).tolist()
            actions.append(
                CleaningActionItem(
                    rule_id="R11",
                    rule_name="Statistical Outlier Flag",
                    column=col_str,
                    before_value=f"{count} outliers (sample: {sample})",
                    after_value=f"Bounds: [{bounds_dict[col_str][0]:.2f}, {bounds_dict[col_str][1]:.2f}]",
                    reason=f"Flagged {count} outliers using {method.upper()} rule (Tukey 1.5x IQR / Modified Z-Score).",
                    severity=Severity.WARNING.value,
                )
            )

    return outlier_counts, bounds_dict, actions


def handle_missing_values(
    df: pd.DataFrame,
    numeric_strategy: str = "flag",
    category_strategy: str = "flag",
) -> Tuple[pd.DataFrame, List[CleaningActionItem]]:
    """
    R12: Missing-value handling strategy tied to statistics.
    Default: 'flag' only.
    Opt-in: 'median' imputation for numeric columns (median robust to outliers),
            'unknown' filling for categorical columns.
    """
    actions: List[CleaningActionItem] = []
    clean_df = df.copy()

    for col in clean_df.columns:
        series = clean_df[col]
        missing_count = series.isna().sum()
        if missing_count == 0:
            continue

        pct = (missing_count / len(series)) * 100.0
        col_str = str(col)

        # Severe missingness warning (> 50%)
        if pct > 50.0:
            actions.append(
                CleaningActionItem(
                    rule_id="R12",
                    rule_name="High Missingness Alert",
                    column=col_str,
                    before_value=f"{pct:.1f}% missing ({missing_count} rows)",
                    after_value="Flagged in Report",
                    reason=f"Column '{col_str}' has > 50% missingness ({pct:.1f}%). Imputation is discouraged due to bias.",
                    severity=Severity.DANGER.value,
                )
            )

        # Numeric column strategy
        if pd.api.types.is_numeric_dtype(series):
            if numeric_strategy == "median":
                med_val = float(series.median())
                clean_df[col] = clean_df[col].fillna(med_val)
                actions.append(
                    CleaningActionItem(
                        rule_id="R12",
                        rule_name="Median Imputation",
                        column=col_str,
                        before_value=f"{missing_count} NaN values",
                        after_value=f"Imputed with median={med_val:.2f}",
                        reason=f"Opt-in median imputation applied to '{col_str}'. Median chosen for robustness against skewed distributions.",
                        severity=Severity.INFO.value,
                    )
                )
            elif numeric_strategy == "mean":
                mean_val = float(series.mean())
                clean_df[col] = clean_df[col].fillna(mean_val)
                actions.append(
                    CleaningActionItem(
                        rule_id="R12",
                        rule_name="Mean Imputation",
                        column=col_str,
                        before_value=f"{missing_count} NaN values",
                        after_value=f"Imputed with mean={mean_val:.2f}",
                        reason=f"Opt-in mean imputation applied to '{col_str}'. Note: may attenuate variance.",
                        severity=Severity.INFO.value,
                    )
                )
        else:
            # Categorical column strategy
            if category_strategy == "unknown":
                clean_df[col] = clean_df[col].fillna("Unknown")
                actions.append(
                    CleaningActionItem(
                        rule_id="R12",
                        rule_name="Category Fill",
                        column=col_str,
                        before_value=f"{missing_count} NaN values",
                        after_value="Filled with 'Unknown'",
                        reason=f"Filled missing category values in '{col_str}' with 'Unknown' to preserve row membership.",
                        severity=Severity.INFO.value,
                    )
                )

    return clean_df, actions


def check_cross_column_consistency(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[CleaningActionItem]]:
    """
    R14: Cross-column consistency checks.
    E.g., graduation_date >= enrollment_date, birth_date < enrollment_date.
    """
    actions: List[CleaningActionItem] = []
    cols_lower = {str(c).lower(): c for c in df.columns}

    # Date ordering checks: (start_date, end_date)
    date_pairs = [
        ("enrollment_date", "graduation_date"),
        ("admit_date", "graduation_date"),
        ("start_date", "end_date"),
        ("birth_date", "enrollment_date"),
        ("dob", "enrollment_date"),
    ]

    for start_key, end_key in date_pairs:
        if start_key in cols_lower and end_key in cols_lower:
            start_col = cols_lower[start_key]
            end_col = cols_lower[end_key]

            # Convert to datetime series
            s_dates = pd.to_datetime(df[start_col], errors="coerce")
            e_dates = pd.to_datetime(df[end_col], errors="coerce")

            valid_mask = s_dates.notna() & e_dates.notna()
            conflict_mask = valid_mask & (e_dates < s_dates)
            conflict_count = conflict_mask.sum()

            if conflict_count > 0:
                sample_rows = df[conflict_mask].index.tolist()[:5]
                actions.append(
                    CleaningActionItem(
                        rule_id="R14",
                        rule_name="Cross-Column Date Conflict",
                        column=f"{start_col} vs {end_col}",
                        before_value=f"{conflict_count} records where {end_col} < {start_col}",
                        after_value="Flagged in Report",
                        reason=f"Found {conflict_count} records where chronological order is inverted ({end_col} is before {start_col}). Rows: {sample_rows}.",
                        severity=Severity.DANGER.value,
                    )
                )

    return df, actions
