"""
Server-side data aggregation and chart preparation engine.
Executes fast, vectorized aggregations in pandas to produce
optimized JSON payloads for Chart.js 4 without streaming raw datasets to the browser.
Validates all column names against the dataset schema to eliminate injection risks.
"""

import json
import os
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from scipy import stats
from apps.uploads.models import Upload


def load_cleaned_dataframe(upload: Upload) -> pd.DataFrame:
    """Load cleaned dataset from CSV or XLSX with caching."""
    if upload.cleaned_csv and os.path.exists(upload.cleaned_csv.path):
        return pd.read_csv(upload.cleaned_csv.path)
    elif upload.cleaned_file and os.path.exists(upload.cleaned_file.path):
        return pd.read_excel(upload.cleaned_file.path, sheet_name=0)
    else:
        raise FileNotFoundError("Cleaned dataset not available.")


def apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """Apply column-level filter criteria."""
    filtered_df = df.copy()

    for col, criteria in filters.items():
        if col not in filtered_df.columns:
            continue

        if isinstance(criteria, list):
            # Category in list: ['Science', 'Engineering']
            filtered_df = filtered_df[filtered_df[col].isin(criteria)]
        elif isinstance(criteria, dict):
            # Numeric or date range: {'min': 2.0, 'max': 4.0}
            if "min" in criteria and criteria["min"] is not None:
                filtered_df = filtered_df[filtered_df[col] >= float(criteria["min"])]
            if "max" in criteria and criteria["max"] is not None:
                filtered_df = filtered_df[filtered_df[col] <= float(criteria["max"])]
            if "from" in criteria and criteria["from"]:
                filtered_df = filtered_df[filtered_df[col] >= str(criteria["from"])]
            if "to" in criteria and criteria["to"]:
                filtered_df = filtered_df[filtered_df[col] <= str(criteria["to"])]
        elif criteria is not None and str(criteria).strip() != "":
            filtered_df = filtered_df[filtered_df[col] == criteria]

    return filtered_df


def aggregate_chart_data(
    upload: Upload,
    chart_type: str,
    x_col: Optional[str] = None,
    y_col: Optional[str] = None,
    agg_func: str = "mean",
    bins: int = 12,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Computes server-side aggregated chart payload for Chart.js 4.
    """
    df = load_cleaned_dataframe(upload)
    allowed_columns = set(df.columns)

    if filters:
        df = apply_filters(df, filters)

    total_records = len(df)

    # 1. Histogram
    if chart_type == "histogram":
        if not x_col or x_col not in allowed_columns:
            # Default to first numeric column
            num_cols = df.select_dtypes(include=[np.number]).columns
            x_col = num_cols[0] if len(num_cols) > 0 else df.columns[0]

        series = pd.to_numeric(df[x_col], errors="coerce").dropna()
        if len(series) == 0:
            return {"chart_type": "histogram", "labels": [], "data": [], "count": 0}

        counts, bin_edges = np.histogram(series, bins=max(5, min(50, bins)))
        labels = [f"{bin_edges[i]:.1f} - {bin_edges[i+1]:.1f}" for i in range(len(counts))]

        return {
            "chart_type": "histogram",
            "x_column": x_col,
            "labels": labels,
            "datasets": [
                {
                    "label": f"Frequency ({x_col})",
                    "data": [int(c) for c in counts],
                    "backgroundColor": "rgba(99, 102, 241, 0.6)",
                    "borderColor": "rgba(99, 102, 241, 1)",
                    "borderWidth": 1,
                }
            ],
            "stats": {
                "mean": round(float(series.mean()), 2),
                "median": round(float(series.median()), 2),
                "std": round(float(series.std()), 2) if len(series) > 1 else 0.0,
                "count": len(series),
            },
        }

    # 2. Bar Chart
    elif chart_type == "bar":
        if not x_col or x_col not in allowed_columns:
            # Pick first categorical column
            cat_cols = [c for c in df.columns if df[c].dtype == object or str(df[c].dtype) == "category"]
            x_col = cat_cols[0] if cat_cols else df.columns[0]

        if y_col and y_col in allowed_columns and pd.api.types.is_numeric_dtype(df[y_col]):
            # Aggregation by category
            if agg_func == "sum":
                grouped = df.groupby(x_col)[y_col].sum()
            elif agg_func == "median":
                grouped = df.groupby(x_col)[y_col].median()
            elif agg_func == "min":
                grouped = df.groupby(x_col)[y_col].min()
            elif agg_func == "max":
                grouped = df.groupby(x_col)[y_col].max()
            else:  # default mean
                grouped = df.groupby(x_col)[y_col].mean()

            grouped = grouped.sort_values(ascending=False).head(20)
            labels = [str(k) for k in grouped.index]
            data = [round(float(v), 2) for v in grouped.values]
            label_text = f"{agg_func.capitalize()} of {y_col} by {x_col}"
        else:
            # Simple value counts
            counts = df[x_col].value_counts().head(20)
            labels = [str(k) for k in counts.index]
            data = [int(v) for v in counts.values]
            label_text = f"Record Count by {x_col}"

        return {
            "chart_type": "bar",
            "x_column": x_col,
            "y_column": y_col,
            "agg": agg_func,
            "labels": labels,
            "datasets": [
                {
                    "label": label_text,
                    "data": data,
                    "backgroundColor": "rgba(79, 70, 229, 0.7)",
                    "borderColor": "rgba(79, 70, 229, 1)",
                    "borderWidth": 1,
                    "borderRadius": 4,
                }
            ],
            "total_records": total_records,
        }

    # 3. Line Chart
    elif chart_type == "line":
        if not x_col or x_col not in allowed_columns:
            # Default to date column or first column
            date_cols = [c for c in df.columns if "date" in str(c).lower() or "year" in str(c).lower()]
            x_col = date_cols[0] if date_cols else df.columns[0]

        if not y_col or y_col not in allowed_columns or not pd.api.types.is_numeric_dtype(df[y_col]):
            # If no numeric y, count by x
            grouped = df.groupby(x_col).size().sort_index()
            labels = [str(k) for k in grouped.index]
            data = [int(v) for v in grouped.values]
            label_text = f"Count over {x_col}"
        else:
            # Aggregate y by x
            if agg_func == "sum":
                grouped = df.groupby(x_col)[y_col].sum().sort_index()
            else:
                grouped = df.groupby(x_col)[y_col].mean().sort_index()

            labels = [str(k) for k in grouped.index]
            data = [round(float(v), 2) for v in grouped.values]
            label_text = f"{agg_func.capitalize()} {y_col} over {x_col}"

        return {
            "chart_type": "line",
            "x_column": x_col,
            "y_column": y_col,
            "labels": labels,
            "datasets": [
                {
                    "label": label_text,
                    "data": data,
                    "borderColor": "rgba(16, 185, 129, 1)",
                    "backgroundColor": "rgba(16, 185, 129, 0.1)",
                    "fill": True,
                    "tension": 0.3,
                }
            ],
        }

    # 4. Pie / Doughnut
    elif chart_type in ["pie", "doughnut"]:
        if not x_col or x_col not in allowed_columns:
            cat_cols = [c for c in df.columns if df[c].dtype == object]
            x_col = cat_cols[0] if cat_cols else df.columns[0]

        counts = df[x_col].value_counts()
        # Keep top 8, group rest as "Other"
        if len(counts) > 8:
            top = counts.head(7)
            other_sum = counts.iloc[7:].sum()
            labels = [str(k) for k in top.index] + ["Other"]
            data = [int(v) for v in top.values] + [int(other_sum)]
        else:
            labels = [str(k) for k in counts.index]
            data = [int(v) for v in counts.values]

        palette = [
            "rgba(99, 102, 241, 0.8)",
            "rgba(16, 185, 129, 0.8)",
            "rgba(245, 158, 11, 0.8)",
            "rgba(239, 68, 68, 0.8)",
            "rgba(139, 92, 246, 0.8)",
            "rgba(14, 165, 233, 0.8)",
            "rgba(236, 72, 153, 0.8)",
            "rgba(100, 116, 139, 0.8)",
        ]

        return {
            "chart_type": chart_type,
            "x_column": x_col,
            "labels": labels,
            "datasets": [
                {
                    "data": data,
                    "backgroundColor": palette[: len(labels)],
                    "borderWidth": 1,
                }
            ],
        }

    # 5. Scatter Plot (with trendline and Pearson r)
    elif chart_type == "scatter":
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(num_cols) < 2:
            return {"chart_type": "scatter", "error": "At least 2 numeric columns required for scatter plot."}

        x_c = x_col if (x_col and x_col in num_cols) else num_cols[0]
        y_c = y_col if (y_col and y_col in num_cols and y_col != x_c) else (num_cols[1] if len(num_cols) > 1 else num_cols[0])

        valid_df = df[[x_c, y_c]].dropna()
        if len(valid_df) == 0:
            return {"chart_type": "scatter", "points": [], "r": 0.0}

        # Subsample to max 1200 points for canvas performance
        if len(valid_df) > 1200:
            sample_df = valid_df.sample(1200, random_state=42)
        else:
            sample_df = valid_df

        points = [{"x": round(float(r[x_c]), 2), "y": round(float(r[y_c]), 2)} for _, r in sample_df.iterrows()]

        # Linear regression trendline
        r_val, p_val = stats.pearsonr(valid_df[x_c], valid_df[y_c])
        slope, intercept, _, _, _ = stats.linregress(valid_df[x_c], valid_df[y_c])

        min_x = float(valid_df[x_c].min())
        max_x = float(valid_df[x_c].max())
        trendline = [
            {"x": round(min_x, 2), "y": round(slope * min_x + intercept, 2)},
            {"x": round(max_x, 2), "y": round(slope * max_x + intercept, 2)},
        ]

        return {
            "chart_type": "scatter",
            "x_column": x_c,
            "y_column": y_c,
            "points": points,
            "trendline": trendline,
            "pearson_r": round(float(r_val), 3),
            "p_value": round(float(p_val), 4),
            "sample_size": len(sample_df),
            "total_size": len(valid_df),
        }

    # 6. Correlation Matrix
    elif chart_type == "correlation":
        num_df = df.select_dtypes(include=[np.number])
        if num_df.shape[1] < 2:
            return {"chart_type": "correlation", "error": "Insufficient numeric columns for correlation."}

        corr = num_df.corr(method="pearson").round(3)
        cols = corr.columns.tolist()
        matrix = []
        for i, r_name in enumerate(cols):
            for j, c_name in enumerate(cols):
                matrix.append({
                    "x": c_name,
                    "y": r_name,
                    "v": round(float(corr.loc[r_name, c_name]), 3),
                })

        return {
            "chart_type": "correlation",
            "columns": cols,
            "matrix": matrix,
        }

    return {"error": f"Unsupported chart type '{chart_type}'."}
