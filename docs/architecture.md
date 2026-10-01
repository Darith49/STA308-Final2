# System Architecture & Technical Specifications

**Course:** STA308 Final Project  
**System:** University Data Portal (Django + Chart.js)

---

## 1. High-Level Architectural Flow

```
[ Web Browser ]
      │
      │ 1. POST /uploads/new/ (.xlsx file + config)
      ▼
[ Django Upload View ]
      │
      ├─► Security Validation (Extension, PK\x03\x04 Zip Header, Size <= 20MB, No VBA Macros)
      ├─► UUID File Renaming (Prevents Path Traversal)
      └─► Create Upload Row (status: QUEUED)
      │
      ▼
[ Async Task Runner (Thread / Worker) ]
      │
      ├─► 1. Ingest (openpyxl read_only=True)
      ├─► 2. Structure Detection (R01 - Title & Summary Stripping)
      ├─► 3. Header Normalization (R02 - SQL-Safe snake_case)
      ├─► 4. Formats & Nulls (R03-R05 - Whitespace & Null Unification)
      ├─► 5. Type Coercion (R06 - Numbers, Currencies, Percentages)
      ├─► 6. Date Parsing (R07 - ISO 8601 & Ambiguity Resolution)
      ├─► 7. Deduplication (R08 & R13 - Exact Drops & Key Flags)
      ├─► 8. Fuzzy Categorical Repair (R09 - rapidfuzz Clustering)
      ├─► 9. Validation & Outliers (R10-R14 - Tukey IQR & Cross-Column Logic)
      ├─► 10. Statistical Moments & Normality (Shapiro-Wilk, Correlation Matrix)
      ├─► 11. Formula Injection Sanitization (Prefix '=', '+', '-', '@' with "'")
      └─► 12. Artifact Export (Cleaned .xlsx + Audit Log Sheet, Cleaned .csv)
      │
      ▼
[ Database & Storage (SQLite / PostgreSQL) ]
      │
      ◄── Polling GET /api/uploads/<id>/status/ (L2 Live Update)
      │
[ Interactive Chart.js 4 Dashboard & Report ]
```

---

## 2. Django Application Decomposition

```
portal/
├── manage.py
├── config/                 # Global Django settings, URLs, WSGI
├── apps/
│   ├── accounts/           # User authentication, UserProfile (Role, Department)
│   ├── uploads/            # Upload, Sheet, ColumnProfile, CleaningAction, QualityReport
│   ├── cleaning/           # Pure-Python cleaning engine (ZERO Django imports)
│   │   ├── pipeline.py     # Main orchestrator
│   │   ├── types.py        # Dataclasses & type hints
│   │   ├── profiling.py    # Statistical profiling & quality scoring
│   │   └── rules/          # R01-R14 modular cleaning rules
│   └── dashboards/         # Chart.js 4 view, DashboardConfig, DRF aggregation endpoints
├── static/                 # Portal CSS design system & client assets
├── templates/              # Semantic Bootstrap 5 + custom templates
├── tests/                  # Unit, Integration, Security, and Fixtures
└── docs/                   # Architecture, Rule Catalog, Data Dictionary
```

### Architectural Invariant: Pure-Python Cleaning Package
The `apps.cleaning` package contains **no Django dependencies**. It operates exclusively with standard library tools, `numpy`, `pandas`, `openpyxl`, `scipy`, and `rapidfuzz`. This ensures:
1. Complete testability outside of the web framework.
2. Direct reuse in scientific notebooks, CLI scripts, and ETL pipelines.
3. Clean reporting of algorithm behavior for academic defense.

---

## 3. Security Architecture

1. **Authentication & Multi-Tenant Data Isolation (O6):**
   - Every database query for uploads, column profiles, reports, and dashboards is filtered by `owner=request.user`.
   - Verified by automated tests: accessing another user's dataset ID returns an immediate HTTP 404.
2. **Spreadsheet Ingestion Defense:**
   - Strict `.xlsx` extension validation.
   - Container magic byte verification (`b"PK\x03\x04"`).
   - Zip archive inspection to verify `[Content_Types].xml` and reject macro containers (`vbaProject.bin`).
   - File size capped at 20 MB.
3. **Formula Injection Sanitization (CSV/XLSX Injection):**
   - When exporting cleaned spreadsheets or CSV files, every text cell starting with `=`, `+`, `-`, `@`, `\t`, or `\r` is automatically escaped with a leading single quote (`'`).
4. **Path Traversal Shield:**
   - Raw and cleaned files are stored with random UUID filenames (`uploads/<uuid>.xlsx`), never retaining user-supplied paths.
5. **SQL Injection Immunity:**
   - Dynamic chart aggregation uses strict column name whitelisting against the dataset's validated schema.

---

## 4. Live Update Mechanisms

- **Level 1 (Must):** Filter interactions on the analytics dashboard query the server-side aggregation API (`/api/uploads/<id>/chart-data/`) asynchronously via `fetch()` and update Chart.js canvases with smooth transitions without full-page reloads.
- **Level 2 (Must):** Processing pages poll `/api/uploads/<id>/status/` every 1.2 seconds, rendering real-time progress percentages and current stage text, automatically navigating to the Quality Report when complete.
