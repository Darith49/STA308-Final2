"""
Rule R01 & R02: Header Row Detection & Header Normalization.
Identifies true data header row, discards title/metadata rows,
and cleans column names into pythonic, SQL-safe identifiers.
"""

import re
from typing import List, Tuple, Dict, Any, Optional
import pandas as pd
from apps.cleaning.types import CleaningActionItem, Severity


def detect_header_row(raw_df: pd.DataFrame, max_search_rows: int = 15) -> Tuple[pd.DataFrame, int, List[CleaningActionItem]]:
    """
    R01: Find the true header row in spreadsheets where users included
    title rows, metadata blocks, or blank rows above the data table.

    Heuristic:
    The header row typically has:
    - High proportion of non-empty cells (> 50%)
    - High proportion of string values
    - Few or no pure numbers or dates
    - Unique values across columns
    """
    actions: List[CleaningActionItem] = []
    if raw_df.empty or len(raw_df) <= 1:
        return raw_df, 0, actions

    best_row_idx = 0
    best_score = -1.0

    search_depth = min(max_search_rows, len(raw_df))
    for r in range(search_depth):
        row_values = raw_df.iloc[r].tolist()
        non_null = [v for v in row_values if pd.notna(v) and str(v).strip() != ""]
        if not non_null:
            continue

        str_count = sum(1 for v in non_null if isinstance(v, str) and not v.strip().replace(".", "", 1).isdigit())
        unique_count = len(set(str(v).strip().lower() for v in non_null))
        
        # Scoring based on string ratio, non-null ratio, and uniqueness
        non_null_ratio = len(non_null) / max(1, len(row_values))
        str_ratio = str_count / max(1, len(non_null))
        unique_ratio = unique_count / max(1, len(non_null))

        # We heavily penalize single-cell title rows (e.g. merged title row with only 1 string)
        if len(non_null) <= 2 and len(row_values) > 3:
            score = 0.1
        else:
            score = (non_null_ratio * 0.4) + (str_ratio * 0.4) + (unique_ratio * 0.2)

        if score > best_score:
            best_score = score
            best_row_idx = r

    # Promote detected header row to columns and slice data
    new_headers = raw_df.iloc[best_row_idx].tolist()
    clean_df = raw_df.iloc[best_row_idx + 1:].copy().reset_index(drop=True)
    clean_df.columns = new_headers

    # If the detected header row is > 0, log discarding title rows
    if best_row_idx > 0:
        actions.append(
            CleaningActionItem(
                rule_id="R01",
                rule_name="Header Row Detection",
                row_ref=best_row_idx + 1,
                before_value=f"Rows 1-{best_row_idx} treated as metadata/title",
                after_value=f"Promoted row {best_row_idx + 1} to table header",
                reason=f"Detected title/notes rows above table. Discarded {best_row_idx} leading rows.",
                severity=Severity.INFO.value,
            )
        )

    # Drop trailing summary / total rows (e.g. "Total", "Average", "Grand Total")
    tail_check_idx = len(clean_df) - 1
    while tail_check_idx >= 0:
        row_str = " ".join([str(v).strip().lower() for v in clean_df.iloc[tail_check_idx] if pd.notna(v)])
        if any(marker in row_str for marker in ["total", "grand total", "average", "summary", "count:"]):
            actions.append(
                CleaningActionItem(
                    rule_id="R01",
                    rule_name="Trailing Summary Row Removal",
                    row_ref=tail_check_idx + 1,
                    before_value=row_str[:60],
                    after_value="Removed",
                    reason="Identified and dropped trailing summary/aggregate row to preserve raw record integrity.",
                    severity=Severity.INFO.value,
                )
            )
            clean_df = clean_df.iloc[:tail_check_idx].copy()
            tail_check_idx -= 1
        else:
            break

    return clean_df, best_row_idx, actions


def normalize_headers(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str], List[CleaningActionItem]]:
    """
    R02: Normalize column headers:
    - Trim whitespace
    - Lowercase
    - Replace whitespace and special characters with underscores
    - Fill empty headers with 'column_N'
    - Deduplicate collision headers (e.g., 'score', 'score_2')
    """
    actions: List[CleaningActionItem] = []
    clean_df = df.copy()
    old_columns = list(clean_df.columns)
    new_columns: List[str] = []
    seen: Dict[str, int] = {}
    mapping: Dict[str, str] = {}

    for i, col in enumerate(old_columns):
        raw_name = str(col).strip() if pd.notna(col) else ""
        
        # If unnamed or empty
        if not raw_name or raw_name.lower().startswith("unnamed:"):
            base_name = f"column_{i + 1}"
        else:
            # Lowercase and replace non-alphanumeric chars with underscore
            base_name = raw_name.lower()
            base_name = re.sub(r"[^\w\s]", "", base_name)
            base_name = re.sub(r"\s+", "_", base_name).strip("_")
            if not base_name:
                base_name = f"column_{i + 1}"

        # Deduplicate
        if base_name in seen:
            seen[base_name] += 1
            final_name = f"{base_name}_{seen[base_name]}"
        else:
            seen[base_name] = 1
            final_name = base_name

        new_columns.append(final_name)
        mapping[str(col)] = final_name

        if str(col) != final_name:
            actions.append(
                CleaningActionItem(
                    rule_id="R02",
                    rule_name="Header Normalization",
                    column=final_name,
                    before_value=str(col),
                    after_value=final_name,
                    reason="Standardized column name to lowercase alphanumeric snake_case identifier.",
                    severity=Severity.INFO.value,
                )
            )

    clean_df.columns = new_columns
    return clean_df, mapping, actions
