"""
Rule R07: Date Parsing and Ambiguity Detection.
Normalizes mixed date formats, converts Excel serial numbers,
and flags ambiguous day/month representations.
"""

from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from apps.cleaning.types import CleaningActionItem, Severity


def excel_serial_to_date(serial: float) -> Optional[datetime]:
    """Convert Excel serial number (e.g. 44927) to Python datetime."""
    try:
        # Excel's epoch starts Dec 30 1899 due to 1900 leap year bug
        base_date = datetime(1899, 12, 30)
        return base_date + timedelta(days=float(serial))
    except Exception:
        return None


def parse_date_series(
    series: pd.Series, ambiguous_preference: str = "DMY"
) -> Tuple[pd.Series, bool, int, int]:
    """
    Attempts to parse a Series into datetime.
    Returns (parsed_series, had_ambiguity, parsed_count, failure_count).
    """
    dayfirst = (ambiguous_preference.upper() == "DMY")
    had_ambiguity = False
    parsed_values: List[Optional[str]] = []
    parsed_count = 0
    failure_count = 0

    for val in series:
        if pd.isna(val) or str(val).strip() == "":
            parsed_values.append(np.nan)
            continue

        # Check if already datetime/Timestamp
        if isinstance(val, (pd.Timestamp, datetime)):
            parsed_values.append(val.strftime("%Y-%m-%d"))
            parsed_count += 1
            continue

        # Check for numeric Excel serial (e.g., numbers between 30000 and 60000 = 1982 to 2064)
        if isinstance(val, (int, float)) and 20000 <= val <= 70000:
            dt = excel_serial_to_date(val)
            if dt:
                parsed_values.append(dt.strftime("%Y-%m-%d"))
                parsed_count += 1
                continue

        s = str(val).strip()

        # Check ambiguous pattern like 03/04/2024 or 03-04-2024 (both day and month <= 12)
        parts = []
        for sep in ["/", "-", "."]:
            if sep in s:
                p = s.split(sep)
                if len(p) == 3 and p[0].isdigit() and p[1].isdigit() and p[2].isdigit():
                    n1, n2 = int(p[0]), int(p[1])
                    if 1 <= n1 <= 12 and 1 <= n2 <= 12 and n1 != n2:
                        had_ambiguity = True
                break

        import warnings
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                dt = pd.to_datetime(s, dayfirst=dayfirst, errors="raise")
            parsed_values.append(dt.strftime("%Y-%m-%d"))
            parsed_count += 1
        except Exception:
            # Fallback to dateutil without dayfirst
            try:
                dt = pd.to_datetime(s, errors="coerce")
                if pd.notna(dt):
                    parsed_values.append(dt.strftime("%Y-%m-%d"))
                    parsed_count += 1
                else:
                    parsed_values.append(np.nan)
                    failure_count += 1
            except Exception:
                parsed_values.append(np.nan)
                failure_count += 1

    return pd.Series(parsed_values, index=series.index), had_ambiguity, parsed_count, failure_count


def parse_dates(
    df: pd.DataFrame,
    date_columns: Optional[List[str]] = None,
    ambiguous_preference: str = "DMY",
    min_date_ratio: float = 0.70,
) -> Tuple[pd.DataFrame, List[str], List[CleaningActionItem]]:
    """
    R07: Detects and standardizes date columns into ISO 8601 YYYY-MM-DD.
    Logs ambiguous date assumptions and parse counts.
    """
    actions: List[CleaningActionItem] = []
    clean_df = df.copy()
    detected_date_cols: List[str] = []

    for col in clean_df.columns:
        col_str = str(col).lower()
        is_date_named = any(
            kw in col_str
            for kw in ["date", "dob", "birth", "enrolled", "graduated", "timestamp", "start_date", "end_date", "admit"]
        )

        # Skip already numeric columns if not explicitly named date
        if pd.api.types.is_numeric_dtype(clean_df[col]) and not is_date_named:
            continue

        non_null_count = clean_df[col].dropna().shape[0]
        if non_null_count == 0:
            continue

        # If user explicitly specified columns or name matches, or let's test a sample
        if is_date_named or (date_columns and col in date_columns):
            parsed_series, ambiguous, parsed_cnt, fail_cnt = parse_date_series(
                clean_df[col], ambiguous_preference=ambiguous_preference
            )
            ratio = parsed_cnt / max(1, non_null_count)
            if ratio >= 0.50:
                clean_df[col] = parsed_series
                detected_date_cols.append(str(col))

                reason_str = f"Normalized {parsed_cnt} date values to ISO 8601 (YYYY-MM-DD)."
                if ambiguous:
                    reason_str += f" Ambiguous day/month format detected; resolved using {ambiguous_preference} precedence."
                    severity = Severity.WARNING.value
                else:
                    severity = Severity.INFO.value

                actions.append(
                    CleaningActionItem(
                        rule_id="R07",
                        rule_name="Date Standardization",
                        column=str(col),
                        before_value="Mixed/non-standard date representations",
                        after_value="ISO 8601 (YYYY-MM-DD)",
                        reason=reason_str,
                        severity=severity,
                    )
                )

                if fail_cnt > 0:
                    actions.append(
                        CleaningActionItem(
                            rule_id="R07",
                            rule_name="Unparseable Date Anomaly",
                            column=str(col),
                            before_value=f"{fail_cnt} values",
                            after_value="NaN",
                            reason=f"{fail_cnt} invalid or unparseable date values were converted to NaN in column '{col}'.",
                            severity=Severity.WARNING.value,
                        )
                    )

    return clean_df, detected_date_cols, actions
