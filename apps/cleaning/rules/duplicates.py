"""
Rules R08 & R13: Exact Duplicate Removal & Key Duplicate Detection.
Removes identical duplicate records (keeping the first occurrence)
and flags semantic key duplicates without silent data destruction.
"""

from typing import List, Tuple, Optional
import pandas as pd
from apps.cleaning.types import CleaningActionItem, Severity


def remove_exact_duplicates(df: pd.DataFrame) -> Tuple[pd.DataFrame, int, List[CleaningActionItem]]:
    """
    R08: Detect and drop exact duplicate rows (all columns identical).
    Keeps the first occurrence and logs the action.
    """
    actions: List[CleaningActionItem] = []
    initial_count = len(df)

    if initial_count == 0:
        return df, 0, actions

    # Identify duplicate rows
    dup_mask = df.duplicated(keep="first")
    dup_count = dup_mask.sum()

    if dup_count > 0:
        dup_indices = df[dup_mask].index.tolist()[:10]
        clean_df = df[~dup_mask].copy().reset_index(drop=True)

        actions.append(
            CleaningActionItem(
                rule_id="R08",
                rule_name="Exact Duplicate Removal",
                before_value=f"{dup_count} exact duplicate rows",
                after_value=f"Dropped {dup_count} rows (kept first occurrences)",
                reason=f"Removed {dup_count} fully redundant identical rows (indices sample: {dup_indices}).",
                severity=Severity.INFO.value,
            )
        )
        return clean_df, dup_count, actions

    return df.copy(), 0, actions


def detect_key_duplicates(
    df: pd.DataFrame, key_columns: Optional[List[str]] = None
) -> Tuple[pd.DataFrame, int, List[CleaningActionItem]]:
    """
    R13: Identify records that duplicate a unique business identifier
    (e.g., student_id), but contain conflicting attributes.
    Per project plan principle: FLAGS only, never silently deletes.
    """
    actions: List[CleaningActionItem] = []
    if df.empty:
        return df, 0, actions

    # Infer potential ID column if not explicitly provided
    candidate_keys = key_columns or []
    if not candidate_keys:
        for col in df.columns:
            col_l = str(col).lower()
            if col_l in ["student_id", "id", "student_number", "record_id", "user_id"]:
                candidate_keys = [str(col)]
                break

    if not candidate_keys:
        return df, 0, actions

    # Filter to existing columns
    valid_keys = [k for k in candidate_keys if k in df.columns]
    if not valid_keys:
        return df, 0, actions

    # Find duplicates on key columns
    key_dup_mask = df.duplicated(subset=valid_keys, keep=False)
    key_dup_count = key_dup_mask.sum()

    if key_dup_count > 0:
        sample_keys = df.loc[key_dup_mask, valid_keys].drop_duplicates().head(5).to_dict(orient="records")
        actions.append(
            CleaningActionItem(
                rule_id="R13",
                rule_name="Key Duplicate Detection",
                column=", ".join(valid_keys),
                before_value=f"{key_dup_count} records sharing key(s)",
                after_value="Flagged in report (retained)",
                reason=(
                    f"Found {key_dup_count} rows with duplicate primary keys on {valid_keys}. "
                    f"Sample colliding keys: {sample_keys}. Rows preserved to avoid silent data loss."
                ),
                severity=Severity.WARNING.value,
            )
        )

    return df, key_dup_count, actions
