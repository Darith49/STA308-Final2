# University Data Portal

STA308 Final Project - Statistical Data Cleaning, Quality Profiling & University Management

A Django 5 web application engineered for automated, reproducible data cleaning and quality profiling of university spreadsheets (.xlsx). Features a 14-stage pure-Python cleaning pipeline, transactional domain ingestion, role-based access control, server-side data scoping, and live-updating Chart.js dashboards.

---

## Role-Based Architecture

The system routes users to dedicated portals based on their assigned role:

### 1. Administrator (Full Control)
- System-wide dashboard with cross-department KPIs and performance charts.
- User management: create users, assign roles and departments, deactivate/activate accounts, and reset passwords.
- Curriculum management: CRUD for departments, academic programs, and courses.
- System audit log: tracking all logins, uploads, deletions, modifications, and exports.
- Upload deletion: rolls back all domain database rows linked to the upload.

### 2. Registrar (Data Owner)
- Starter template downloads for each dataset type (Courses, Students, Grades, Attendance) with example data and rules sheets.
- Uploads XLSX datasets in order: Courses, then Students, then Grades, then Attendance.
- Validates file security (.xlsx format, size limits, signature check, no macros, duplicate SHA-256 prevention, and schema validation).
- Automated cleaning pipeline: cleans headers, removes duplicates, repairs typos, standardizes categories, and detects outliers.
- Transactional ingestion: valid records are bulk-inserted; invalid records are saved to an error log.
- Downloadable error file (.xlsx) listing rejected rows, column names, and failure reasons.
- Deleting an upload rolls back only that upload's imported rows.

### 3. Department Head / Lecturer (Read-Only, Own Department)
- Scoped department dashboard: strictly limited to the user's assigned department at the database level.
- KPIs: total students, active courses, average grades, pass rates, and attendance rate.
- Dynamic Chart.js visualizations: score distribution, pass rate by course, and attendance ratios.
- Live filter bar: filter charts by semester, program, and course via asynchronous API updates without page reload.
- Browse records: paginated and searchable tables for students, courses, grades, and attendance.
- Protected CSV export: exports filtered records with formula injection sanitization.
- Password management: update credentials for own account.

### 4. Student (Stretch Goal)
- Student self-service portal: scoped strictly to the authenticated student's personal records.
- Transcript view: course grades, numerical scores, letter grades, GPA points, and completion status.
- Attendance tracker: session presence, tardiness, and overall attendance rate.
- GPA trend chart: interactive visualization of term-by-term GPA progression.
- Profile editing: update contact information and account password.

---

## Security and Data Scoping

- Request lifecycle: Request -> Logged in? -> Role allowed? -> Data scoped to role (scope_for) -> Response.
- Unauthorized access attempts are rejected with an HTTP 403 Forbidden page.
- Scoping occurs in database queries, preventing URL manipulation from exposing unauthorized departmental data.
- Formula injection protection shields all exported CSV files by neutralizing leading formula symbols (=, +, -, @).

---

## Quickstart Guide

### 1. Clone the repository
```bash
git clone https://github.com/Darith49/STA308-Final2.git
cd STA308-Final2
```

### 2. Set up virtual environment
```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run database migrations
```bash
python manage.py migrate
```

### 5. Seed demo accounts and sample data
```bash
python seed_demo.py
```

### 6. Start development server
```bash
python manage.py runserver
```
Visit http://127.0.0.1:8000 in your browser.

---

## Pre-Configured Demo Accounts

All demo accounts share the password: `password123`

| Role | Username | Password | Default Landing Page |
| :--- | :--- | :--- | :--- |
| Administrator | admin_demo | password123 | /academic/admin/overview/ |
| Registrar | registrar_demo | password123 | /uploads/ |
| Department Head | depthead_demo | password123 | /academic/department/dashboard/ |
| Student | student_demo | password123 | /academic/student/portal/ |

---

## Running Automated Tests

Run the full test suite covering cleaning rules, security sanitization, role authorization, and data scoping:

```bash
python manage.py test tests.test_cleaning_pipeline tests.test_security_and_api tests.test_role_architecture
```

Run benchmarks and evaluation metrics:
```bash
python evaluate_cleaning.py
```
