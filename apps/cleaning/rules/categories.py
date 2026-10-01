"""
Rule R09: Categorical Casing and Typo Repair via Fuzzy Matching.
Normalizes letter casing and clusters near-duplicate strings to dominant values.
"""

from typing import List, Tuple, Dict, Any
from collections import Counter
import pandas as pd
from apps.cleaning.types import CleaningActionItem, Severity

try:
    from rapidfuzz import fuzz, process
    HAS_RAPIDFUZZ = True
except ImportError:
    import difflib
    HAS_RAPIDFUZZ = False


def similarity_score(s1: str, s2: str) -> float:
    """Compute string similarity (0 to 100)."""
    if HAS_RAPIDFUZZ:
        return fuzz.token_sort_ratio(s1, s2)
    else:
        return difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio() * 100.0


def clean_categories(
    df: pd.DataFrame,
    fuzzy_threshold: float = 85.0,
    max_unique_cardinality: int = 150
) -> Tuple[pd.DataFrame, List[CleaningActionItem]]:
    """
    R09: Case normalization and typo repair for categorical columns.
    Maps rare variants/misspellings to the most frequent canonical variant.
    """
    actions: List[CleaningActionItem] = []
    clean_df = df.copy()

    for col in clean_df.columns:
        series = clean_df[col]
        # Only check string/object columns
        if not (series.dtype == object or pd.api.types.is_string_dtype(series)):
            continue

        non_null = series.dropna()
        if len(non_null) == 0:
            continue

        # Check cardinality: categorical typically has limited unique values
        n_unique = non_null.nunique()
        if n_unique > max_unique_cardinality or n_unique <= 1:
            continue

        # Skip explicit ID or long text columns
        col_lower = str(col).lower()
        if any(term in col_lower for term in ["id", "code", "notes", "description", "address", "email"]):
            continue

        # Step 1: Normalize casing to title-case if letters
        # We compute frequency distribution of stripped values
        counts = Counter(non_null.astype(str).str.strip())
        
        # Sort values by frequency descending (canonical candidates are the most frequent)
        sorted_values = [val for val, count in counts.most_common()]
        
        # Mapping from variant to canonical
        mapping: Dict[str, str] = {}
        canonical_pool: List[str] = []

        for candidate in sorted_values:
            cand_clean = candidate.strip()
            if not cand_clean:
                continue

            matched_canonical = None
            best_score = 0.0

            # Compare against existing canonical pool
            for canonical in canonical_pool:
                score = similarity_score(cand_clean, canonical)
                if score >= fuzzy_threshold and score > best_score:
                    best_score = score
                    matched_canonical = canonical

            if matched_canonical and matched_canonical != cand_clean:
                mapping[cand_clean] = matched_canonical
            else:
                # Becomes its own canonical cluster center
                canonical_pool.append(cand_clean)

        # Apply mapping
        if mapping:
            for variant, canonical in mapping.items():
                variant_mask = (clean_df[col].astype(str).str.strip() == variant)
                count_replaced = variant_mask.sum()
                if count_replaced > 0:
                    clean_df.loc[variant_mask, col] = canonical
                    actions.append(
                        CleaningActionItem(
                            rule_id="R09",
                            rule_name="Category Typo Repair",
                            column=str(col),
                            before_value=f"'{variant}' ({count_replaced} occurrences)",
                            after_value=f"'{canonical}'",
                            reason=f"Repaired categorical misspelling/variant in '{col}' via fuzzy clustering (similarity >= {fuzzy_threshold}%).",
                            severity=Severity.INFO.value,
                        )
                    )

    return clean_df, actions
