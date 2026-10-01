"""
Rules R03, R04, R05: Empty Rows/Cols Removal, Whitespace Trimming, and Null Unification.
"""

from typing import List, Tuple, Set
import numpy as np
import pandas as pd
from apps.cleaning.types import CleaningActionItem, Severity

# Recognized common missing/null representations
NULL_TOKENS: Set[str] = {
    "", "nan", "null", "none", "n/a", "na", "n.a.", "#n/a", "#na",
    "-", "--", "---", ".", "?", "missing", "unknown", "nil", "undefined"
}


def drop_empty_rows_cols(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[CleaningActionItem]]:
    """
    R03: Drop rows and columns that are 100% empty/NaN.
    """
    actions: List[CleaningActionItem] = []
    initial_rows = len(df)
    initial_cols = len(df.columns)

    # First replace blank spaces with NaN temporarily to check all-null
    temp_df = df.replace(r"^\s*$", np.nan, regex=True)

    # Drop all-null columns
    valid_cols = temp_df.dropna(axis=1, how="all").columns
    dropped_cols = [c for c in df.columns if c not in valid_cols]
    clean_df = df[valid_cols].copy()

    for col in dropped_cols:
        actions.append(
            CleaningActionItem(
                rule_id="R03",
                rule_name="Drop Empty Column",
                column=str(col),
                before_value="100% Empty Column",
                after_value="Removed",
                reason=f"Dropped empty column '{col}' containing no non-null values.",
                severity=Severity.INFO.value,
            )
        )

    # Drop all-null rows
    temp_clean = clean_df.replace(r"^\s*$", np.nan, regex=True)
    non_empty_mask = ~temp_clean.isna().all(axis=1)
    clean_df = clean_df[non_empty_mask].copy().reset_index(drop=True)

    rows_dropped = initial_rows - len(clean_df)
    if rows_dropped > 0:
        actions.append(
            CleaningActionItem(
                rule_id="R03",
                rule_name="Drop Empty Rows",
                before_value=f"{rows_dropped} empty rows",
                after_value="Removed",
                reason=f"Removed {rows_dropped} completely blank rows from dataset.",
                severity=Severity.INFO.value,
            )
        )

    return clean_df, actions


def trim_whitespace(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[CleaningActionItem]]:
    """
    R04: Trim leading and trailing whitespace and condense multiple internal spaces.
    """
    actions: List[CleaningActionItem] = []
    clean_df = df.copy()
    trimmed_count = 0

    for col in clean_df.columns:
        if clean_df[col].dtype == object or pd.api.types.is_string_dtype(clean_df[col]):
            series = clean_df[col].astype(str)
            # Find elements with leading/trailing spaces
            mask = series.str.match(r"^\s+|\s+$", na=False)
            count = mask.sum()
            if count > 0:
                trimmed_count += count
                # Clean: strip whitespace and reduce multiple internal spaces to 1
                clean_df[col] = clean_df[col].apply(
                    lambda x: " ".join(str(x).split()) if pd.notna(x) and not isinstance(x, (int, float, bool)) else x
                )
                actions.append(
                    CleaningActionItem(
                        rule_id="R04",
                        rule_name="Whitespace Trim",
                        column=str(col),
                        before_value=f"{count} cells with excessive whitespace",
                        after_value="Trimmed whitespace",
                        reason=f"Stripped leading/trailing whitespace and normalized spaces across column '{col}'.",
                        severity=Severity.INFO.value,
                    )
                )

    return clean_df, actions


def unify_null_tokens(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[CleaningActionItem]]:
    """
    R05: Unify disparate textual representations of missingness
    (e.g., 'N/A', '-', 'None', 'null', '?', '#N/A') into uniform np.nan.
    """
    actions: List[CleaningActionItem] = []
    clean_df = df.copy()

    for col in clean_df.columns:
        if clean_df[col].dtype == object or pd.api.types.is_string_dtype(clean_df[col]):
            # Check for tokens
            series = clean_df[col].astype(str).str.strip().str.lower()
            mask = series.isin(NULL_TOKENS) & clean_df[col].notna()
            matched_count = mask.sum()

            if matched_count > 0:
                # Get unique tokens matched for reporting
                matched_tokens = clean_df.loc[mask, col].unique().tolist()[:5]
                clean_df.loc[mask, col] = np.nan
                actions.append(
                    CleaningActionItem(
                        rule_id="R05",
                        rule_name="Null Token Unification",
                        column=str(col),
                        before_value=f"{matched_count} tokens {matched_tokens}",
                        after_value="NaN",
                        reason=f"Unified {matched_count} non-standard null tokens in '{col}' to true NaN.",
                        severity=Severity.INFO.value,
                    )
                )

    return clean_df, actions
