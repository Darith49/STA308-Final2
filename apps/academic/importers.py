"""
Domain record validator and transactional bulk-importer for University datasets.
Validates cleaned DataFrames, records row-level errors into UploadError,
and bulk-inserts valid records within an atomic database transaction.
"""

import re
import datetime
import pandas as pd
from django.db import transaction
from django.utils.dateparse import parse_date

from apps.academic.models import Department, Program, Course, Student, Grade, Attendance, score_to_letter_and_gpa
from apps.uploads.models import Upload, UploadError


def normalize_column_lookup(df: pd.DataFrame) -> dict:
    """Map normalized snake_case column names to actual dataframe column names."""
    lookup = {}
    for col in df.columns:
        norm = re.sub(r"[^\w\s]", "", str(col).strip().lower())
        norm = re.sub(r"\s+", "_", norm)
        lookup[norm] = col
    return lookup


def import_domain_dataset(upload: Upload, clean_df: pd.DataFrame) -> int:
    """
    Main dispatcher for dataset domain import.
    Returns the count of successfully inserted valid rows.
    """
    dtype = upload.dataset_type
    if dtype == "courses":
        return import_courses(upload, clean_df)
    elif dtype == "students":
        return import_students(upload, clean_df)
    elif dtype == "grades":
        return import_grades(upload, clean_df)
    elif dtype == "attendance":
        return import_attendance(upload, clean_df)
    return 0


def import_courses(upload: Upload, df: pd.DataFrame) -> int:
    lookup = normalize_column_lookup(df)
    col_code = lookup.get("course_code") or lookup.get("code")
    col_title = lookup.get("title") or lookup.get("course_title") or lookup.get("name")
    col_dept = lookup.get("department_code") or lookup.get("department") or lookup.get("dept")
    col_prog = lookup.get("program_code") or lookup.get("program")
    col_cred = lookup.get("credits") or lookup.get("credit_hours")
    col_sem = lookup.get("semester") or lookup.get("term")

    departments_cache = {d.code.upper(): d for d in Department.objects.all()}
    # Also index departments by name for flexibility
    for d in Department.objects.all():
        departments_cache[d.name.upper()] = d

    programs_cache = {p.code.upper(): p for p in Program.objects.all()}
    existing_codes = set(Course.objects.values_list("code", flat=True))

    valid_courses = []
    errors = []
    seen_in_file = set()

    for idx, row in df.iterrows():
        row_num = idx + 2  # 1-indexed header + 1
        raw_code = str(row[col_code]).strip() if col_code and pd.notna(row[col_code]) else ""
        raw_title = str(row[col_title]).strip() if col_title and pd.notna(row[col_title]) else ""
        raw_dept = str(row[col_dept]).strip().upper() if col_dept and pd.notna(row[col_dept]) else ""

        if not raw_code:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="course_code", raw_value="", reason="Course code cannot be empty"))
            continue
        if raw_code in seen_in_file:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="course_code", raw_value=raw_code, reason=f"Duplicate course code '{raw_code}' in uploaded file"))
            continue
        if raw_code in existing_codes:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="course_code", raw_value=raw_code, reason=f"Course code '{raw_code}' already exists in database"))
            continue
        if not raw_title:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="title", raw_value="", reason="Course title cannot be empty"))
            continue

        dept = departments_cache.get(raw_dept)
        if not dept:
            # If department not found, check if we should auto-create it or report error
            # Per spec: "Admin sets up departments... before any upload happens"
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="department_code", raw_value=raw_dept, reason=f"Department '{raw_dept}' does not exist. Please create department first."))
            continue

        prog = None
        if col_prog and pd.notna(row[col_prog]):
            raw_prog = str(row[col_prog]).strip().upper()
            prog = programs_cache.get(raw_prog)

        credits = 3
        if col_cred and pd.notna(row[col_cred]):
            try:
                credits = int(float(row[col_cred]))
                if credits < 1 or credits > 12:
                    credits = 3
            except (ValueError, TypeError):
                credits = 3

        semester = "Fall 2026"
        if col_sem and pd.notna(row[col_sem]):
            semester = str(row[col_sem]).strip()

        seen_in_file.add(raw_code)
        valid_courses.append(
            Course(
                department=dept,
                program=prog,
                code=raw_code,
                title=raw_title,
                credits=credits,
                semester=semester,
                upload=upload,
            )
        )

    with transaction.atomic():
        if valid_courses:
            Course.objects.bulk_create(valid_courses)
        if errors:
            UploadError.objects.bulk_create(errors)

    return len(valid_courses)


def import_students(upload: Upload, df: pd.DataFrame) -> int:
    lookup = normalize_column_lookup(df)
    col_id = lookup.get("student_id") or lookup.get("id")
    col_fn = lookup.get("first_name") or lookup.get("firstname") or lookup.get("fname")
    col_ln = lookup.get("last_name") or lookup.get("lastname") or lookup.get("lname")
    col_email = lookup.get("email") or lookup.get("email_address")
    col_dept = lookup.get("department_code") or lookup.get("department") or lookup.get("dept")
    col_prog = lookup.get("program_code") or lookup.get("program")
    col_cohort = lookup.get("cohort") or lookup.get("enrollment_year")
    col_status = lookup.get("status") or lookup.get("enrollment_status")

    departments_cache = {d.code.upper(): d for d in Department.objects.all()}
    for d in Department.objects.all():
        departments_cache[d.name.upper()] = d

    programs_cache = {p.code.upper(): p for p in Program.objects.all()}
    existing_ids = set(Student.objects.values_list("student_id", flat=True))

    valid_students = []
    errors = []
    seen_in_file = set()
    email_regex = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    for idx, row in df.iterrows():
        row_num = idx + 2
        raw_id = str(row[col_id]).strip() if col_id and pd.notna(row[col_id]) else ""
        raw_fn = str(row[col_fn]).strip() if col_fn and pd.notna(row[col_fn]) else ""
        raw_ln = str(row[col_ln]).strip() if col_ln and pd.notna(row[col_ln]) else ""
        raw_email = str(row[col_email]).strip().lower() if col_email and pd.notna(row[col_email]) else ""
        raw_dept = str(row[col_dept]).strip().upper() if col_dept and pd.notna(row[col_dept]) else ""

        if not raw_id:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="student_id", raw_value="", reason="Student ID is required"))
            continue
        if raw_id in seen_in_file:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="student_id", raw_value=raw_id, reason=f"Duplicate Student ID '{raw_id}' in file"))
            continue
        if raw_id in existing_ids:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="student_id", raw_value=raw_id, reason=f"Student ID '{raw_id}' already exists in database"))
            continue
        if not raw_fn or not raw_ln:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="name", raw_value=f"{raw_fn} {raw_ln}".strip(), reason="First and last names are required"))
            continue
        if not raw_email or not email_regex.match(raw_email):
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="email", raw_value=raw_email, reason=f"Invalid email address '{raw_email}'"))
            continue

        dept = departments_cache.get(raw_dept)
        if not dept:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="department_code", raw_value=raw_dept, reason=f"Department '{raw_dept}' does not exist"))
            continue

        prog = None
        if col_prog and pd.notna(row[col_prog]):
            prog = programs_cache.get(str(row[col_prog]).strip().upper())

        cohort = str(row[col_cohort]).strip() if col_cohort and pd.notna(row[col_cohort]) else "2024"
        raw_st = str(row[col_status]).strip().capitalize() if col_status and pd.notna(row[col_status]) else "Active"
        status = raw_st if raw_st in ["Active", "Graduated", "Suspended"] else "Active"

        seen_in_file.add(raw_id)
        valid_students.append(
            Student(
                student_id=raw_id,
                first_name=raw_fn,
                last_name=raw_ln,
                email=raw_email,
                department=dept,
                program=prog,
                cohort=cohort,
                status=status,
                upload=upload,
            )
        )

    with transaction.atomic():
        if valid_students:
            Student.objects.bulk_create(valid_students)
        if errors:
            UploadError.objects.bulk_create(errors)

    return len(valid_students)


def import_grades(upload: Upload, df: pd.DataFrame) -> int:
    lookup = normalize_column_lookup(df)
    col_sid = lookup.get("student_id") or lookup.get("id")
    col_code = lookup.get("course_code") or lookup.get("code")
    col_score = lookup.get("numerical_score") or lookup.get("score") or lookup.get("grade")
    col_sem = lookup.get("semester") or lookup.get("term")

    students_cache = {s.student_id.upper(): s for s in Student.objects.all()}
    courses_cache = {c.code.upper(): c for c in Course.objects.all()}

    valid_grades = []
    errors = []
    seen_keys = set()

    for idx, row in df.iterrows():
        row_num = idx + 2
        raw_sid = str(row[col_sid]).strip().upper() if col_sid and pd.notna(row[col_sid]) else ""
        raw_code = str(row[col_code]).strip().upper() if col_code and pd.notna(row[col_code]) else ""
        semester = str(row[col_sem]).strip() if col_sem and pd.notna(row[col_sem]) else "Fall 2026"

        if not raw_sid:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="student_id", raw_value="", reason="Student ID is required"))
            continue
        student = students_cache.get(raw_sid)
        if not student:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="student_id", raw_value=raw_sid, reason=f"Student '{raw_sid}' not found in database. Upload Students first."))
            continue

        if not raw_code:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="course_code", raw_value="", reason="Course code is required"))
            continue
        course = courses_cache.get(raw_code)
        if not course:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="course_code", raw_value=raw_code, reason=f"Course '{raw_code}' not found in database. Upload Courses first."))
            continue

        # Score parsing & range checking (0 - 100)
        score_val = None
        raw_score = str(row[col_score]).strip() if col_score and pd.notna(row[col_score]) else ""
        try:
            score_val = float(re.sub(r"[^\d\.]", "", raw_score))
        except (ValueError, TypeError):
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="numerical_score", raw_value=raw_score, reason=f"Invalid numeric score '{raw_score}'"))
            continue

        if score_val < 0.0 or score_val > 100.0:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="numerical_score", raw_value=str(score_val), reason=f"Score {score_val} is outside valid range (0–100)"))
            continue

        dedup_key = (student.id, course.id, semester.lower())
        if dedup_key in seen_keys:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="grade", raw_value=f"{raw_sid}:{raw_code}", reason=f"Duplicate grade entry for student in course '{raw_code}' for term '{semester}'"))
            continue

        seen_keys.add(dedup_key)
        letter, pts, is_pass = score_to_letter_and_gpa(score_val)
        valid_grades.append(
            Grade(
                student=student,
                course=course,
                semester=semester,
                numerical_score=score_val,
                letter_grade=letter,
                gpa_points=pts,
                passed=is_pass,
                upload=upload,
            )
        )

    with transaction.atomic():
        if valid_grades:
            Grade.objects.bulk_create(valid_grades)
        if errors:
            UploadError.objects.bulk_create(errors)

    return len(valid_grades)


def import_attendance(upload: Upload, df: pd.DataFrame) -> int:
    lookup = normalize_column_lookup(df)
    col_sid = lookup.get("student_id") or lookup.get("id")
    col_code = lookup.get("course_code") or lookup.get("code")
    col_date = lookup.get("date") or lookup.get("session_date") or lookup.get("attendance_date")
    col_status = lookup.get("status") or lookup.get("attendance_status")
    col_topic = lookup.get("session_topic") or lookup.get("topic")

    students_cache = {s.student_id.upper(): s for s in Student.objects.all()}
    courses_cache = {c.code.upper(): c for c in Course.objects.all()}

    valid_attendance = []
    errors = []
    valid_statuses = {"Present", "Absent", "Late", "Excused"}

    for idx, row in df.iterrows():
        row_num = idx + 2
        raw_sid = str(row[col_sid]).strip().upper() if col_sid and pd.notna(row[col_sid]) else ""
        raw_code = str(row[col_code]).strip().upper() if col_code and pd.notna(row[col_code]) else ""

        if not raw_sid:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="student_id", raw_value="", reason="Student ID is required"))
            continue
        student = students_cache.get(raw_sid)
        if not student:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="student_id", raw_value=raw_sid, reason=f"Student '{raw_sid}' not found in database"))
            continue

        if not raw_code:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="course_code", raw_value="", reason="Course code is required"))
            continue
        course = courses_cache.get(raw_code)
        if not course:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="course_code", raw_value=raw_code, reason=f"Course '{raw_code}' not found in database"))
            continue

        # Parse Date
        date_obj = None
        raw_date = row[col_date] if col_date and pd.notna(row[col_date]) else None
        if raw_date is not None:
            if isinstance(raw_date, (datetime.date, datetime.datetime)):
                date_obj = raw_date.date() if isinstance(raw_date, datetime.datetime) else raw_date
            else:
                date_str = str(raw_date).split(" ")[0].strip()
                date_obj = parse_date(date_str)
                if not date_obj:
                    try:
                        date_obj = pd.to_datetime(date_str).date()
                    except Exception:
                        pass

        if not date_obj:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="date", raw_value=str(raw_date), reason=f"Invalid date format '{raw_date}'. Expected YYYY-MM-DD"))
            continue

        raw_status = str(row[col_status]).strip().capitalize() if col_status and pd.notna(row[col_status]) else "Present"
        if raw_status not in valid_statuses:
            errors.append(UploadError(upload=upload, row_number=row_num, column_name="status", raw_value=raw_status, reason=f"Invalid status '{raw_status}'. Must be Present, Absent, Late, or Excused"))
            continue

        topic = str(row[col_topic]).strip() if col_topic and pd.notna(row[col_topic]) else ""

        valid_attendance.append(
            Attendance(
                student=student,
                course=course,
                date=date_obj,
                status=raw_status,
                session_topic=topic,
                upload=upload,
            )
        )

    with transaction.atomic():
        if valid_attendance:
            Attendance.objects.bulk_create(valid_attendance)
        if errors:
            UploadError.objects.bulk_create(errors)

    return len(valid_attendance)
