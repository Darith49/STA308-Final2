# University Data Portal

> **"From messy Excel files to trusted, visual insights in one click."**

The **University Data Portal** is an end-to-end, role-scoped academic data ingestion, cleaning, and analytics platform. It replaces manual, error-prone spreadsheet tracking with automated validation, transparent explainable data cleaning, strict database normalization, and live interactive dashboards.

---

## 🎯 Key Objectives & Features

1. **Role-Based Access Control (RBAC):**
   - **Admin:** University-wide visibility, dataset uploads, user management, and upload rollbacks.
   - **Registrar:** University-wide visibility, dataset uploads, and rollback of own uploads.
   - **Dept Head / Lecturer:** Strictly department-scoped dashboards, course analytics, and student records.
   - **Student:** Personalized student view of own course enrollments, letter grades, and attendance history.
   - *Enforced server-side on every view and API endpoint via `RoleRequiredMixin` and `scope_for(user)`.*

2. **Automated, Explainable Cleaning Pipeline:**
   - **Stage 1 (Structural):** Case-insensitive header alias mapping (e.g. `Student Number` &rarr; `student_id`), whitespace stripping, empty row/column elimination, and business key deduplication.
   - **Stage 2 (Type Conversion):** Number and date parsing across multiple international date formats.
   - **Stage 3 (Standardization):** Canonical mapping for gender (`m`/`f` &rarr; `Male`/`Female`), departments, programs, and attendance (`present`/`1` &rarr; `P`, `absent`/`0` &rarr; `A`, `late`/`tardy` &rarr; `L`).
   - **Stage 4 (Validation):** Row-level constraint verification (missing keys, score range `0-100`, year range `1-6`, future dates, and foreign key integrity).
   - **Stage 5 (Atomic Ingestion):** `transaction.atomic()`, `bulk_create(batch_size=500)`, exact row-by-row error traceability, and JSON report generation.

3. **Traceability & Rollback:**
   - **Cleaning Report:** Metrics cards breakdown and error logs linking each rejected cell directly to its Excel row number.
   - **Error XLSX Export:** One-click download of an Excel spreadsheet containing only rejected rows with exact error reasons.
   - **Cascade Rollback:** Deleting an upload rolls back all associated database rows in a single atomic transaction.
   - **Audit Trail:** Immutable audit log tracking spreadsheet uploads, rollbacks, and account modifications.

4. **Live Scoped Dashboards:**
   - Powered by **Chart.js** with asynchronous `fetch()` API updates on filter changes (Department, Semester, Course).
   - KPI metric cards: Total Students, Active Courses, Average Score, Pass Rate, Monthly Ingestion Volume.
   - Charts: Students by Department (Bar), Year Distribution (Doughnut), Enrollment Trend (Line), Grade Distribution (Column), Course Pass Rates (Horizontal Bar), and Attendance Trends (Line).

5. **Security Hardening:**
   - `LoginRequiredMiddleware` enforcing authentication across the portal by default.
   - Upload security: Strict `.xlsx` only, file size cap (5 MB), openpyxl `read_only=True` inspection, cell count limits, and SHA-256 duplicate detection.
   - CSV formula injection protection: Prefixes cells starting with `=`, `+`, `-`, `@`, `\t`, `\r` with `'`.

---

## 🏗️ Architecture & Repository Structure

```
portal/
├── config/
│   ├── settings/ (base.py, dev.py, prod.py)
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
├── accounts/          # Roles (Profile), Permissions, Middleware, User CRUD, Audit Logs
├── academics/         # Department, Program, Course, Student, Enrollment, Attendance
├── uploads/           # Upload, UploadError, forms, validators, background tasks
├── analytics/         # Chart & KPI REST endpoints, role scoping (scope_for)
├── services/
│   ├── cleaners/      # Pure cleaners: base.py, students.py, courses.py, grades.py, attendance.py
│   ├── importers.py   # Bulk import engine and error XLSX generator
│   └── templates_xlsx.py # Downloadable XLSX template generator
├── templates/         # Clean UI templates (Bootstrap 5.3 + FontAwesome)
├── static/
│   ├── css/portal.css # Design system & typography
│   └── js/charts.js   # Dynamic Chart.js renderer & upload polling
├── sample_data/       # 4 clean + 4 deliberately messy Excel spreadsheets + generator
├── tests/             # Comprehensive pytest suite (Cleaners, Permissions, Importers, API)
├── Dockerfile & docker-compose.yml
├── manage.py & requirements.txt
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.11+
- Virtual environment (recommended)

### 2. Setup & Installation
```bash
# Clone and enter directory
cd "Assignment STA"

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Seed database with initial departments, courses, and demo accounts
python manage.py seed_demo

# Start the development server
python manage.py runserver
```

Open your browser to: **`http://127.0.0.1:8000/`**

---

## 👥 Demo User Accounts

All pre-seeded test accounts use the password: **`Password123!`**

| Username | Role | Department Scope | Key Permissions |
| :--- | :--- | :--- | :--- |
| `admin` | **Admin** | University-wide | Full access, user management, delete any upload |
| `registrar` | **Registrar** | University-wide | Ingest spreadsheets, rollback own uploads |
| `dept_head` | **Dept Head** | Computer Science (`CS`) | Scoped analytics & student lists for CS only |
| `student` | **Student** | Linked Student (`STU1001`) | Personal grades, enrolled courses, attendance |

*(The login page includes quick one-click credential buttons for immediate testing).*

---

## 📊 Sample Data Files (`sample_data/`)

Pre-generated sample spreadsheets are ready to test the ingestion pipeline:

| Dataset | Clean File | Deliberately Messy File (Test Case) |
| :--- | :--- | :--- |
| **Students** | `students_clean.xlsx` | `students_messy.xlsx` *(duplicate IDs, lowercase depts, year 99, invalid email, future date)* |
| **Courses** | `courses_clean.xlsx` | `courses_messy.xlsx` *(missing codes, duplicate codes, invalid credits)* |
| **Grades** | `grades_clean.xlsx` | `grades_messy.xlsx` *(scores > 100, negative scores, unknown student IDs, non-numeric grades)* |
| **Attendance** | `attendance_clean.xlsx` | `attendance_messy.xlsx` *(future dates, unknown status strings, status variations 'present'/'0')* |

To regenerate sample files at any time:
```bash
python sample_data/generate_sample_data.py
```

---

## 🧪 Testing & Validation

The test suite contains 22 automated tests covering unit cleaner logic, permission matrices, API contracts, and bulk importer rollback behavior:

```bash
# Run the full test suite
pytest
```

---

## 🐳 Docker Deployment

To launch the portal with PostgreSQL, Redis, and a Celery worker:

```bash
docker-compose up --build
```
Access the application at `http://localhost:8000`.
