import re
from datetime import datetime, date
import pandas as pd
import numpy as np

class BaseCleaner:
    """
    Base Cleaner providing structural preprocessing, header normalization,
    whitespace cleaning, deduplication, and error recording.
    Pure functions - no Django ORM dependency inside cleaner methods.
    """
    HEADER_ALIASES = {}
    BUSINESS_KEYS = []
    REQUIRED_COLUMNS = []

    def __init__(self):
        self.errors = []
        self.report = {
            'rows_in': 0,
            'empty_rows_removed': 0,
            'duplicates_removed': 0,
            'categories_standardized': 0,
            'values_adjusted': 0,
            'rows_ok': 0,
            'rows_rejected': 0,
        }

    def record_error(self, row_num, column, value, message):
        self.errors.append({
            'row_number': int(row_num),
            'column': str(column),
            'value': str(value) if value is not None and not pd.isna(value) else '',
            'message': str(message)
        })

    def normalize_headers(self, df):
        """
        Normalize column headers: strip, lowercase, spaces/special chars to underscore,
        and map known aliases to canonical column names.
        """
        new_cols = []
        for col in df.columns:
            cleaned = str(col).strip().lower()
            cleaned = re.sub(r'[\s\-\.]+', '_', cleaned)
            # Check alias map
            matched = False
            for canonical, aliases in self.HEADER_ALIASES.items():
                if cleaned == canonical or cleaned in aliases:
                    new_cols.append(canonical)
                    matched = True
                    break
            if not matched:
                new_cols.append(cleaned)
        df.columns = new_cols
        return df

    def strip_whitespace(self, df):
        """Strip whitespace from all object/string columns."""
        for col in df.columns:
            if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
                df[col] = df[col].apply(lambda v: v.strip() if isinstance(v, str) else v)
        return df

    def drop_empty_rows_and_cols(self, df):
        """Remove rows and columns that are entirely null or whitespace."""
        init_rows = len(df)
        # Drop columns that are completely empty
        df = df.dropna(how='all', axis=1)
        # Drop rows that are completely empty
        df = df.dropna(how='all', axis=0)
        empty_dropped = init_rows - len(df)
        self.report['empty_rows_removed'] += empty_dropped
        return df

    def deduplicate(self, df):
        """Deduplicate rows by business key, keeping last and counting removed duplicates."""
        if not self.BUSINESS_KEYS:
            return df
        
        # Only deduplicate if business keys exist in dataframe
        available_keys = [k for k in self.BUSINESS_KEYS if k in df.columns]
        if not available_keys:
            return df

        init_len = len(df)
        # Identify duplicates
        dup_mask = df.duplicated(subset=available_keys, keep='last')
        dup_count = dup_mask.sum()
        if dup_count > 0:
            self.report['duplicates_removed'] += int(dup_count)
            # Keep last occurrence
            df = df.drop_duplicates(subset=available_keys, keep='last').copy()
        return df

    def clean(self, df):
        """Subclasses must implement dataset-specific cleaning pipeline."""
        raise NotImplementedError("Subclasses must implement clean(df)")
