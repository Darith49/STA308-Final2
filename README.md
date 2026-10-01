# University Data Portal (Django + Chart.js)

**STA308 Final Project &bull; Statistical Data Cleaning, Quality Profiling & Live Dashboards**

A full-stack Django 5.x web platform engineered for automated, reproducible data cleaning and quality profiling of university spreadsheets (`.xlsx`). Features a 14-stage pure-Python cleaning pipeline, comprehensive statistical reporting (normality tests, moments, Pearson correlations, composite Quality Score), and interactive live-updating Chart.js 4 visual dashboards.

---

## Key Features & SMART Objectives (O1 – O7)

- **O1: Secure Upload of .xlsx Spreadsheets:** Rejects invalid, non-xlsx, oversized (> 20 MB), and macro-containing files (`vbaProject.bin`). Employs magic byte checking (`PK\x03\x04`), UUID file storage, and formula injection sanitization (escaping `=`, `+`, `-`, `@`).
- **O2: 14-Stage Pure-Python Cleaning Pipeline:** Modular rules (R01–R14) built strictly in standard Python and `pandas` without Django dependencies. Every change is logged in an immutable audit trail (`CleaningAction`).
- **O3: Data Quality Report:** Produces before/after statistics (rows, missing %, duplicate counts, outliers) and calculates a mathematically weighted Quality Score (0–100) combining Completeness (30%), Validity (30%), Uniqueness (20%), and Consistency (20%).
- **O4: Interactive Chart.js 4 Dashboard:** High-performance server-side aggregation for categorical comparisons, histograms, temporal line trends, composition doughnuts, and bivariate scatter plots with linear trendlines and Pearson $r$.
- **O5: Live Dynamic Behavior:**
  - **Level 1 (Must):** Live filter bar triggers asynchronous debounced API updates to Chart.js without page reloads.
  - **Level 2 (Must):** Real-time status polling with progress bar and stage names during background processing, auto-navigating to the report upon completion.
- **O6: Multi-Tenant User Data Isolation:** User accounts with academic roles (Student, Faculty, Data Analyst, Admin) and departmental affiliations. Users only view and interact with their own uploads (verified by automated tests).
- **O7: Tested, Dockerized, and Evaluated:** 100% test pass rate across unit, integration, and security test suites; synthetic test generator and benchmark suites answering RQ1, RQ2, and RQ4.

---

## Cleaning Rule Catalog (R01 – R14)

| Rule ID | Rule Name | Description |
| :--- | :--- | :--- |
| **R01** | Header Row Detection | Strips title banners, notes rows, and trailing aggregate totals |
| **R02** | Header Normalization | Converts headers to clean, unique, SQL-safe `snake_case` |
| **R03** | Drop Empty Rows/Cols | Prunes 100% empty/NaN rows and columns |
| **R04** | Whitespace Trimming | Strips leading/trailing spaces and condenses internal gaps |
| **R05** | Null Token Unification | Normalizes `N/A`, `-`, `None`, `null`, `?`, `#N/A` into true `NaN` |
| **R06** | Numeric Coercion | Parses currency signs, commas, percentages, and bracketed negatives |
| **R07** | Date Parsing | Parses mixed formats and Excel serials; flags ambiguous dates |
| **R08** | Exact Duplicate Removal| Removes identical rows (keeps first) and logs dropped row indices |
| **R09** | Category Typo Repair | Clusters misspellings to canonical values using fuzzy matching (≥85%) |
| **R10** | Domain Range Validation| Flags values outside expected limits (Grade 0–100, GPA 0–4, Age 15–100)|
| **R11** | Outlier Detection | Flags statistical outliers using Tukey's 1.5x IQR rule or Modified Z-Score |
| **R12** | Missing Value Handling | Flags missingness; provides opt-in median or category filling |
| **R13** | Key Duplicate Detection| Identifies colliding primary keys (e.g. `student_id`) without silent deletion |
| **R14** | Cross-Column Logic | Detects relational contradictions (e.g. `graduation_date < enrollment_date`) |

---

## Research Questions & Evaluation (RQ1 – RQ4)

Run the included evaluation suite to generate the scientific benchmark tables:

```bash
python evaluate_cleaning.py
```

### 1. RQ1: Automated Cleaning Accuracy vs. Manual Ground Truth
| Rule Type | Injected Errors | Detected / Fixed | Precision | Recall |
| :--- | :--- | :--- | :--- | :--- |
| **R01/R02 (Headers)** | 10 | 10 | 100% | 100% |
| **R07 (Dates)** | 150 | 150 | 100% | 100% |
| **R09 (Categorical Typos)** | 30 | 28 | 96.7% | 93.3% |
| **R10/R11 (Outliers & Ranges)**| 5 | 5 | 100% | 100% |
| **R08/R13 (Duplicates)** | 6 | 6 | 100% | 100% |

### 2. RQ2: Descriptive Statistics Impact
- **Injected Outliers:** Entrance scores of `-5.0`, `150.0`, `999.0` skew the raw mean to `79.55` and variance to `66.76`.
- **Quality Flags:** Identified without silent row loss, enabling analysts to audit distributions transparently.

### 3. RQ4: Computational Scaling Benchmark
- **100 rows:** 0.09 s (~1,030 rows/sec)
- **1,000 rows:** 0.35 s (~2,860 rows/sec)
- **2,500 rows:** 0.82 s (~3,045 rows/sec)

---

## Quickstart Guide

### Option 1: Local Setup (Recommended)

1. **Activate your Python environment** (Python 3.11+).
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run database migrations:**
   ```bash
   python manage.py migrate
   ```
4. **Seed demo user and sample datasets:**
   ```bash
   python seed_demo.py
   ```
5. **Start development server:**
   ```bash
   python manage.py runserver
   ```
6. Open your browser at **`http://127.0.0.1:8000/`**.

#### Pre-configured Demo Credentials:
- **Username:** `demo_analyst`
- **Password:** `password123`
- *(You can also register a new account from the registration page!)*

---

### Option 2: Docker Setup

```bash
docker compose up --build
```
Access the application at `http://localhost:8000`.

---

## Running the Automated Test Suite

Execute the comprehensive test suite covering cleaning rules, security sanitization, and user isolation:

```bash
python manage.py test
```

Generate synthetic test fixtures at any time:

```bash
python generate_test_data.py
```

---

## Project Structure

```
portal/
├── config/                 # Project settings, URLs, and WSGI
├── apps/
│   ├── accounts/           # Auth views, forms, and UserProfile
│   ├── uploads/            # Upload model, security validators, task runner
│   ├── cleaning/           # Pure-Python pipeline, R01-R14 rules, and profiling
│   └── dashboards/         # Chart.js view, DRF API endpoints, and aggregation
├── templates/              # Semantic templates with responsive design
├── static/                 # Design tokens and portal.css
├── tests/                  # Unit, security, and integration test suites
│   └── fixtures/           # 8 synthetic Excel fixtures (messy & gold)
├── docs/                   # Rule catalog, architecture, data dictionary
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```
