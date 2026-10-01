"""
Rule R06: Type Inference and Numeric Coercion.
Infers data types per column, standardizes numeric representations
(commas, currency, percentages, negative brackets), and logs coercion anomalies.
"""

import re
from typing import List, Tuple, Dict, Any
import numpy as np
import pandas as pd
from apps.cleaning.types import CleaningActionItem, Severity


def clean_numeric_string(val: Any) -> Any:
    """Helper to sanitize numeric strings like '$1,234.50', '85%', '(50)'."""
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    if not s:
        return np.nan
    
    # Check parenthesized negative: (100) -> -100
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1].strip()

    # Strip currency symbols and commas
    s = re.sub(r"[\$,\s€£¥]", "", s)

    # Strip trailing percentage sign
    if s.endswith("%"):
        s = s[:-1].strip()

    try:
        return float(s)
    except ValueError:
        return val


def coerce_numeric_columns(
    df: pd.DataFrame, majority_threshold: float = 0.80
) -> Tuple[pd.DataFrame, Dict[str, str], List[CleaningActionItem]]:
    """
    R06: Detect columns that are primarily numeric (>= majority_threshold of non-nulls)
    and coerce them safely into floats/integers, logging any cell conversion anomalies.
    """
    actions: List[CleaningActionItem] = []
    clean_df = df.copy()
    inferred_types: Dict[str, str] = {}

    for col in clean_df.columns:
        series = clean_df[col]
        non_null_series = series.dropna()

        # If already numeric, verify int downcasting if lossless
        if pd.api.types.is_numeric_dtype(series):
            # Check if all values are whole numbers
            if (non_null_series % 1 == 0).all() and len(non_null_series) > 0:
                inferred_types[str(col)] = "integer"
            else:
                inferred_types[str(col)] = "float"
            continue

        if len(non_null_series) == 0:
            inferred_types[str(col)] = "text"
            continue

        # Try cleaning candidates
        cleaned_candidates = non_null_series.apply(clean_numeric_string)
        num_mask = cleaned_candidates.apply(lambda x: isinstance(x, (int, float)) and not np.isnan(x))
        numeric_ratio = num_mask.sum() / len(non_null_series)

        # Do not treat pure ID columns like 'student_id', 'ssn' as numeric if they have leading zeros or are explicit IDs
        col_lower = str(col).lower()
        is_id_name = any(kw in col_lower for kw in ["_id", "id_", "ssn", "phone", "zip", "code"]) and not any(kw in col_lower for kw in ["credits", "score", "grade", "gpa", "age", "year", "term", "count"])

        if numeric_ratio >= majority_threshold and not is_id_name:
            # Coerce column
            original_values = clean_df[col].copy()
            coerced_series = pd.to_numeric(
                clean_df[col].apply(clean_numeric_string), errors="coerce"
            )

            # Check if coercion introduced new NaNs (failed cells)
            failed_mask = clean_df[col].notna() & coerced_series.isna()
            failed_count = failed_mask.sum()

            if failed_count > 0:
                sample_failures = original_values[failed_mask].tolist()[:5]
                actions.append(
                    CleaningActionItem(
                        rule_id="R06",
                        rule_name="Numeric Coercion Anomaly",
                        column=str(col),
                        before_value=f"{failed_count} unparseable values: {sample_failures}",
                        after_value="NaN",
                        reason=f"Coerced column '{col}' to numeric. {failed_count} text/malformed cells could not be converted and were set to NaN.",
                        severity=Severity.WARNING.value,
                    )
                )

            # Check if integer
            non_null_coerced = coerced_series.dropna()
            if len(non_null_coerced) > 0 and (non_null_coerced % 1 == 0).all():
                inferred_types[str(col)] = "integer"
                clean_df[col] = coerced_series
            else:
                inferred_types[str(col)] = "float"
                clean_df[col] = coerced_series

            actions.append(
                CleaningActionItem(
                    rule_id="R06",
                    rule_name="Numeric Type Coercion",
                    column=str(col),
                    before_value="string/object representation",
                    after_value=inferred_types[str(col)],
                    reason=f"Standardized numeric formatting (stripped commas, currency, percentages) and cast '{col}' to {inferred_types[str(col)]}.",
                    severity=Severity.INFO.value,
                )
            )
        else:
            inferred_types[str(col)] = "text"

    return clean_df, inferred_types, actions
