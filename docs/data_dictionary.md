# Data Dictionary & Entity-Relationship Schema

This document details the database models, relationships, and data attributes implemented in the University Data Portal.

---

## Entity Relationship Overview

```
User (Django Auth)
  │ 1:1
  ├────────► UserProfile
  │
  │ 1:N
  ├────────► Upload
  │            │
  │            ├─ 1:N ──► Sheet
  │            ├─ 1:N ──► ColumnProfile
  │            ├─ 1:N ──► CleaningAction
  │            ├─ 1:1 ──► QualityReport
  │            └─ 1:N ──► DashboardConfig
  │
  └────────► DashboardConfig
```

---

## 1. `apps.accounts.UserProfile`
Extends Django's `User` model with academic metadata and roles.

| Field | Type | Description |
| :--- | :--- | :--- |
| `user` | OneToOne(User) | Associated authentication user account |
| `role` | CharField(20) | Role: `student`, `faculty`, `analyst`, `admin` |
| `department` | CharField(150) | Department or academic program |
| `created_at` | DateTimeField | Timestamp of account registration |

---

## 2. `apps.uploads.Upload`
Core tracking model for each uploaded spreadsheet.

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Globally unique identifier (prevents enumeration) |
| `owner` | FK(User) | User who uploaded the spreadsheet |
| `original_filename`| CharField(255) | Name of file provided by user |
| `stored_file` | FileField | Path to raw uploaded `.xlsx` file |
| `cleaned_file` | FileField | Path to cleaned `.xlsx` file (with audit sheet) |
| `cleaned_csv` | FileField | Path to sanitized cleaned `.csv` file |
| `sha256` | CharField(64) | SHA-256 cryptographic digest of raw file |
| `size_bytes` | BigIntegerField| File size in bytes |
| `status` | CharField(20) | `QUEUED`, `PROCESSING`, `DONE`, `FAILED` |
| `current_step` | CharField(255) | Human-readable progress description |
| `progress_pct` | IntegerField | Progress percentage (0 - 100) |
| `row_count_raw` | IntegerField | Initial record count |
| `row_count_clean` | IntegerField | Verified clean record count |
| `col_count_clean` | IntegerField | Active column count |
| `quality_score` | FloatField | Composite quality score (0.0 - 100.0) |
| `config_options` | JSONField | Parameter overrides used during cleaning |
| `created_at` | DateTimeField | Timestamp created |
| `finished_at` | DateTimeField | Timestamp processing completed |

---

## 3. `apps.uploads.ColumnProfile`
Statistical characteristics and distribution moments for each column.

| Field | Type | Description |
| :--- | :--- | :--- |
| `upload` | FK(Upload) | Parent upload record |
| `name_raw` | CharField | Original header in spreadsheet |
| `name_clean` | CharField | Standardized snake_case column name |
| `inferred_type` | CharField | Inferred data type (e.g. float64, object) |
| `role` | CharField | Semantic role: `numeric`, `category`, `date`, `id`, `text` |
| `missing_pct_before` | FloatField | Missing percentage before cleaning |
| `missing_pct_after` | FloatField | Missing percentage after cleaning |
| `n_unique` | IntegerField | Number of distinct non-null values |
| `min_val` | FloatField | Minimum numeric value |
| `max_val` | FloatField | Maximum numeric value |
| `mean_val` | FloatField | Arithmetic mean |
| `std_val` | FloatField | Sample standard deviation ($s$) |
| `median_val` | FloatField | Sample median ($\tilde{x}$) |
| `iqr_val` | FloatField | Interquartile range ($Q_3 - Q_1$) |
| `skew_val` | FloatField | Fisher-Pearson skewness coefficient |
| `kurt_val` | FloatField | Sample excess kurtosis |
| `outlier_count` | IntegerField | Count of detected outliers |
| `normality_test` | CharField | Name of statistical test (Shapiro-Wilk) |
| `normality_hint` | TextField | Statistical guidance (e.g., mean vs median recommendation) |

---

## 4. `apps.uploads.CleaningAction`
Immutable audit log recording discrete rule actions.

| Field | Type | Description |
| :--- | :--- | :--- |
| `upload` | FK(Upload) | Parent upload |
| `sheet` | CharField | Sheet name |
| `rule_id` | CharField(20) | Rule code (e.g., `R01`, `R07`, `R09`) |
| `rule_name` | CharField(100) | Human-readable rule title |
| `column` | CharField | Column subject to transformation |
| `row_ref` | IntegerField | Row reference (if applicable) |
| `before_value` | TextField | State before rule execution |
| `after_value` | TextField | State after rule execution |
| `reason` | TextField | Justification for rule execution |
| `severity` | CharField(20) | `info`, `warning`, `danger` |

---

## 5. `apps.uploads.QualityReport`
Composite scoring and quality metrics.

| Field | Type | Description |
| :--- | :--- | :--- |
| `upload` | OneToOne(Upload)| Parent upload |
| `quality_score` | FloatField | Overall Composite Index ($0 - 100$) |
| `completeness_score`| FloatField | $100 \times (1 - \text{missing rate})$ (Weight: 30%) |
| `validity_score` | FloatField | $100 \times (1 - \text{outlier/range rate})$ (Weight: 30%) |
| `uniqueness_score` | FloatField | $100 \times (1 - \text{duplicate rate})$ (Weight: 20%) |
| `consistency_score`| FloatField | $100 \times (1 - \text{contradiction rate})$ (Weight: 20%) |
| `summary_json` | JSONField | Full report payload |
| `correlation_json` | JSONField | Pearson correlation matrix |

---

## 6. `apps.dashboards.DashboardConfig`
Stores custom user dashboard widget layouts.

| Field | Type | Description |
| :--- | :--- | :--- |
| `owner` | FK(User) | Owning user |
| `upload` | FK(Upload) | Associated upload dataset |
| `title` | CharField | Dashboard title |
| `chart_configs` | JSONField | Array of custom widget definitions (type, x, y, agg) |
