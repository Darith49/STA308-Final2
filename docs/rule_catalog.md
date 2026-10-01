# University Data Portal - Data Cleaning Rule Catalog (R01 - R14)

This catalog details the 14 cleaning and validation rules implemented in the pure-Python cleaning engine (`apps.cleaning`). Every rule is logged in the `CleaningAction` audit trail for full scientific reproducibility.

---

## Catalog Summary

| Rule ID | Rule Name | Category | Action Type | Default Status | Destructive? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R01** | Header Row Detection | Structural | Re-index / Drop Title | Enabled | No (discards non-data banners) |
| **R02** | Header Normalization | Structural | Rename Columns | Enabled | No |
| **R03** | Drop Empty Rows & Cols | Structural | Remove | Enabled | Yes (removes 100% empty records) |
| **R04** | Whitespace Trimming | Formatting | Vectorized Strip | Enabled | No |
| **R05** | Null Token Unification | Missingness | Standardize to NaN | Enabled | No |
| **R06** | Numeric Coercion | Type Inference | Cast to Float/Int | Enabled | No |
| **R07** | Date Normalization | Temporal | ISO 8601 Parsing | Enabled | No |
| **R08** | Exact Duplicate Removal | Deduplication | Remove (Keep 1st) | Enabled | Yes (removes redundant rows) |
| **R09** | Category Typo Repair | Categorical | Fuzzy Match / Cluster | Enabled (≥85%)| No |
| **R10** | Domain Range Validation | Validity | Flag Violation | Enabled | No (Flag only) |
| **R11** | Statistical Outliers | Distribution | Tukey IQR / MAD Flag | Enabled | No (Flag only) |
| **R12** | Missing-Value Strategy | Missingness | Flag or Median Impute | Flag (Impute opt-in)| No |
| **R13** | Key Duplicate Detection | Referential | Flag Collisions | Enabled | No (Flag only) |
| **R14** | Cross-Column Consistency| Relational | Flag Contradictions | Enabled | No (Flag only) |

---

## Detailed Rule Specifications

### R01: Header Row Detection
- **Objective:** Locate the authentic tabular header row in files containing title banners, subtitle blocks, or blank rows above the data.
- **Heuristic:** Scans the first $N$ rows (default 15). Scores rows based on: non-empty cell ratio, non-numeric string ratio, and cell uniqueness. Penalizes single-cell merged banner rows.
- **Trailing Removal:** Also scans the bottom of the table to identify and prune aggregate summary rows (e.g., "Grand Total", "Average", "Summary").

### R02: Header Normalization
- **Objective:** Convert arbitrary spreadsheet headers into clean, SQL-safe, snake_case Python identifiers.
- **Transformation:**
  - Strips leading and trailing whitespace.
  - Converts characters to lowercase.
  - Replaces non-alphanumeric characters and whitespace with underscores (`_`).
  - Deduplicates column name collisions (`score`, `score_2`).
  - Fills empty or missing column names with deterministic labels (`column_1`, `column_2`).

### R03: Drop Empty Rows and Columns
- **Objective:** Eliminate completely blank rows and columns that skew missingness proportions and total record counts.
- **Logic:** Identifies rows/columns where 100% of cells are null or whitespace.

### R04: Whitespace Trimming
- **Objective:** Prevent silent categorical mismatches caused by trailing or invisible whitespace.
- **Logic:** Applies vectorized `.strip()` and reduces multi-space sequences to single spaces across all text columns.

### R05: Null Token Unification
- **Objective:** Unify non-standard missing representations into true `np.nan`.
- **Tokens Recognized:** `""`, `"N/A"`, `"NA"`, `"-"`, `"--"`, `"None"`, `"null"`, `"NULL"`, `"?"`, `"#N/A"`, `"missing"`, `"unknown"`.

### R06: Numeric Coercion & Formatting
- **Objective:** Parse formatted numbers into native floats/integers.
- **Handling:**
  - Strips commas (`"1,250.00"` &rarr; `1250.0`).
  - Strips currency signs (`"$500"` &rarr; `500.0`).
  - Strips percent symbols (`"85%"` &rarr; `85.0`).
  - Handles parenthesized accounting negatives (`"(50)"` &rarr; `-50.0`).
  - Preserves IDs (e.g. `student_id`) from numeric coercion.

### R07: Date Normalization & Ambiguity Detection
- **Objective:** Parse mixed date representations into ISO 8601 (`YYYY-MM-DD`).
- **Handling:**
  - Converts Excel serial numbers (e.g., `44927` &rarr; `2023-01-01`).
  - Parses textual formats (`DD/MM/YYYY`, `YYYY-MM-DD`, `DD-Mon-YYYY`).
  - **Ambiguity Detection:** Flags dates where both day and month are $\le 12$ (e.g., `03/04/2024`) and documents the `DMY` vs `MDY` disambiguation precedence.

### R08: Exact Duplicate Removal
- **Objective:** Remove fully redundant records where all attributes are identical.
- **Logic:** Keeps the first occurrence and logs indices of dropped rows.

### R09: Categorical Typo Repair via Fuzzy Matching
- **Objective:** Standardize misspelled categorical entries (e.g., `"Computr Science"` &rarr; `"Computer Science"`).
- **Algorithm:**
  - Uses `rapidfuzz.fuzz.token_sort_ratio` (threshold $\ge 85\%$).
  - Clusters variants around the most frequent canonical spelling in the column.
  - Logs before and after counts.

### R10: Domain Range Validation
- **Objective:** Flag values outside realistic academic domain limits.
- **Default Ranges:**
  - Grade / Exam Score: $[0.0, 100.0]$
  - GPA: $[0.0, 4.0]$
  - Age: $[15.0, 100.0]$
  - Credits: $[0.0, 250.0]$
- **Action:** Flagged with severity `DANGER`; retained to avoid silent data loss.

### R11: Statistical Outlier Flagging
- **Objective:** Detect and flag statistical outliers without arbitrary row deletion.
- **Methods:**
  1. **Tukey's 1.5x IQR Rule:** Outliers $< Q_1 - 1.5 \cdot \text{IQR}$ or $> Q_3 + 1.5 \cdot \text{IQR}$.
  2. **Modified Z-Score (MAD):**
     $$\text{Modified } Z_i = \frac{0.6745 \cdot |x_i - \tilde{x}|}{\text{MAD}} > 3.5$$

### R12: Missing-Value Handling Strategy
- **Objective:** Statistically justifiable treatment of missing data.
- **Rules:**
  - $> 50\%$ missing: Alert raised; imputation discouraged due to attenuation of variance.
  - Numeric strategy: Default `flag`. Opt-in median imputation (median is robust against skewed distributions).
  - Categorical strategy: Default `flag`. Opt-in `Unknown` filling to preserve row membership.

### R13: Key Duplicate Detection
- **Objective:** Detect conflicting records sharing a unique business key (e.g., `student_id`).
- **Action:** Retains records and flags collisions in report.

### R14: Cross-Column Consistency
- **Objective:** Validate relational consistency across coupled columns.
- **Logic:** Chronological checks (e.g., `graduation_date` $\ge$ `enrollment_date`). Inversions flagged with severity `DANGER`.
