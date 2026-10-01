from datetime import date, timedelta
import pandas as pd
import pytest
from services.cleaners import BaseCleaner, StudentsCleaner, CoursesCleaner, GradesCleaner, AttendanceCleaner

def test_base_cleaner_header_normalization():
    cleaner = BaseCleaner()
    cleaner.HEADER_ALIASES = {'student_id': ['id_no', 'student_number']}
    df = pd.DataFrame(columns=['  Student Number ', 'Full Name  ', 'ID_NO'])
    normalized_df = cleaner.normalize_headers(df)
    assert 'student_id' in normalized_df.columns
    assert 'full_name' in normalized_df.columns

def test_base_cleaner_deduplication():
    cleaner = BaseCleaner()
    cleaner.BUSINESS_KEYS = ['id']
    df = pd.DataFrame([
        {'id': '101', 'val': 'first'},
        {'id': '101', 'val': 'second'}
    ])
    res = cleaner.deduplicate(df)
    assert len(res) == 1
    assert res.iloc[0]['val'] == 'second'
    assert cleaner.report['duplicates_removed'] == 1

def test_students_cleaner_valid():
    cleaner = StudentsCleaner()
    df = pd.DataFrame([
        {'student_id': 'STU101', 'name': 'john doe', 'gender': 'm', 'department': 'cs', 'program': 'comp sci', 'year': 2, 'enrollment_date': '2023-09-01', 'email': 'john@test.edu'}
    ])
    clean_df, errors, report = cleaner.clean(df)
    assert report['rows_ok'] == 1
    assert clean_df.iloc[0]['name'] == 'John Doe'
    assert clean_df.iloc[0]['gender'] == 'Male'
    assert clean_df.iloc[0]['year'] == 2

def test_students_cleaner_missing_id_rejected():
    cleaner = StudentsCleaner()
    df = pd.DataFrame([
        {'student_id': '', 'name': 'Nameless'}
    ])
    clean_df, errors, report = cleaner.clean(df)
    assert report['rows_rejected'] == 1
    assert len(clean_df) == 0
    assert any("student_id" in e['column'] for e in errors)

def test_students_cleaner_invalid_year_and_email_warning():
    cleaner = StudentsCleaner()
    df = pd.DataFrame([
        {'student_id': 'STU102', 'name': 'Jane', 'year': 99, 'email': 'not-an-email'}
    ])
    clean_df, errors, report = cleaner.clean(df)
    assert report['rows_ok'] == 1
    assert clean_df.iloc[0]['year'] is None
    assert clean_df.iloc[0]['email'] is None
    assert report['values_adjusted'] >= 2

def test_students_cleaner_future_date_rejected():
    cleaner = StudentsCleaner()
    future_date = (date.today() + timedelta(days=200)).strftime("%Y-%m-%d")
    df = pd.DataFrame([
        {'student_id': 'STU103', 'name': 'Future Man', 'enrollment_date': future_date}
    ])
    clean_df, errors, report = cleaner.clean(df)
    assert report['rows_rejected'] == 1
    assert len(clean_df) == 0

def test_courses_cleaner_valid_and_case():
    cleaner = CoursesCleaner()
    df = pd.DataFrame([
        {'course_code': 'cs101', 'title': 'intro to cs', 'credits': '3', 'department': 'cs'}
    ])
    clean_df, errors, report = cleaner.clean(df)
    assert report['rows_ok'] == 1
    assert clean_df.iloc[0]['course_code'] == 'CS101'
    assert clean_df.iloc[0]['title'] == 'Intro To Cs'
    assert clean_df.iloc[0]['credits'] == 3

def test_courses_cleaner_missing_code_rejected():
    cleaner = CoursesCleaner()
    df = pd.DataFrame([
        {'course_code': '', 'title': 'No Code Course'}
    ])
    clean_df, errors, report = cleaner.clean(df)
    assert report['rows_rejected'] == 1

def test_grades_cleaner_valid_score_and_letter():
    cleaner = GradesCleaner()
    df = pd.DataFrame([
        {'student_id': 'STU1', 'course_code': 'CS101', 'semester': '2024-Fall', 'score': 95.5},
        {'student_id': 'STU2', 'course_code': 'CS101', 'semester': '2024-Fall', 'score': 75.0},
        {'student_id': 'STU3', 'course_code': 'CS101', 'semester': '2024-Fall', 'score': 45.0},
    ])
    clean_df, errors, report = cleaner.clean(df)
    assert report['rows_ok'] == 3
    assert clean_df.iloc[0]['grade_letter'] == 'A'
    assert clean_df.iloc[1]['grade_letter'] == 'C'
    assert clean_df.iloc[2]['grade_letter'] == 'F'

def test_grades_cleaner_invalid_scores_rejected():
    cleaner = GradesCleaner()
    df = pd.DataFrame([
        {'student_id': 'STU1', 'course_code': 'CS101', 'score': 105.0},
        {'student_id': 'STU2', 'course_code': 'CS101', 'score': -5.0},
        {'student_id': 'STU3', 'course_code': 'CS101', 'score': 'N/A'},
    ])
    clean_df, errors, report = cleaner.clean(df)
    assert report['rows_rejected'] == 3
    assert len(clean_df) == 0
    assert report['invalid_scores'] == 3

def test_attendance_cleaner_standardization():
    cleaner = AttendanceCleaner()
    today_str = date.today().strftime("%Y-%m-%d")
    df = pd.DataFrame([
        {'student_id': 'STU1', 'course_code': 'CS101', 'date': today_str, 'status': 'present'},
        {'student_id': 'STU2', 'course_code': 'CS101', 'date': today_str, 'status': '0'},
        {'student_id': 'STU3', 'course_code': 'CS101', 'date': today_str, 'status': 'late'},
    ])
    clean_df, errors, report = cleaner.clean(df)
    assert report['rows_ok'] == 3
    assert list(clean_df['status']) == ['P', 'A', 'L']

def test_attendance_cleaner_invalid_status_and_future_date_rejected():
    cleaner = AttendanceCleaner()
    future_str = (date.today() + timedelta(days=10)).strftime("%Y-%m-%d")
    df = pd.DataFrame([
        {'student_id': 'STU1', 'course_code': 'CS101', 'date': date.today().strftime("%Y-%m-%d"), 'status': 'invalid'},
        {'student_id': 'STU2', 'course_code': 'CS101', 'date': future_str, 'status': 'P'},
    ])
    clean_df, errors, report = cleaner.clean(df)
    assert report['rows_rejected'] == 2
    assert len(clean_df) == 0
