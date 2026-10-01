import os
from datetime import date, timedelta
import pandas as pd
import openpyxl

SAMPLE_DATA_DIR = os.path.dirname(os.path.abspath(__file__))

def create_sample_files():
    print(f"Generating clean and messy sample files in {SAMPLE_DATA_DIR}...")
    today = date.today()

    # ----------------- 1. STUDENTS -----------------
    students_clean_data = [
        {"student_id": "STU2001", "name": "Elena Rostova", "gender": "Female", "department": "CS", "program": "Bachelor of Computer Science", "year": 1, "enrollment_date": "2024-09-01", "email": "elena.r@university.edu"},
        {"student_id": "STU2002", "name": "Marcus Vance", "gender": "Male", "department": "CS", "program": "Bachelor of Computer Science", "year": 2, "enrollment_date": "2023-09-01", "email": "marcus.v@university.edu"},
        {"student_id": "STU2003", "name": "Chloe Bennett", "gender": "Female", "department": "ENG", "program": "Mechanical Engineering", "year": 3, "enrollment_date": "2022-09-01", "email": "chloe.b@university.edu"},
        {"student_id": "STU2004", "name": "David Kim", "gender": "Male", "department": "ENG", "program": "Electrical Engineering", "year": 1, "enrollment_date": "2024-09-01", "email": "david.k@university.edu"},
        {"student_id": "STU2005", "name": "Sophia Martinez", "gender": "Female", "department": "BUS", "program": "Business Administration", "year": 2, "enrollment_date": "2023-09-01", "email": "sophia.m@university.edu"},
    ]
    pd.DataFrame(students_clean_data).to_excel(os.path.join(SAMPLE_DATA_DIR, "students_clean.xlsx"), index=False)

    # Deliberately messy students dataset
    # Tests: header aliases ('Student ID', 'Full Name', 'Sex', 'Dept'), duplicate ID, year > 6, invalid email, future date, missing ID
    students_messy_data = [
        {"Student ID": "STU3001", "Full Name": "  john doe  ", "Sex": "m", "Dept": "cs", "Program": "comp sci", "Year": 1, "Enrollment Date": "01/09/2024", "Email": "john.doe@university.edu"},
        {"Student ID": "STU3001", "Full Name": "John Doe", "Sex": "Male", "Dept": "CS", "Program": "Computer Science", "Year": 1, "Enrollment Date": "2024-09-01", "Email": "john.doe@university.edu"},  # Duplicate ID
        {"Student ID": "STU3002", "Full Name": "JANE SMITH", "Sex": "F", "Dept": "eng", "Program": "mech eng", "Year": 9, "Enrollment Date": "15/09/2023", "Email": "invalid-email-format"},  # year out of range, malformed email
        {"Student ID": "", "Full Name": "Ghost Student", "Sex": "Other", "Dept": "BUS", "Program": "Business", "Year": 2, "Enrollment Date": "2023-09-01", "Email": "ghost@uni.edu"},  # Missing ID (rejected)
        {"Student ID": "STU3004", "Full Name": "Time Traveler", "Sex": "Female", "Dept": "CS", "Program": "Computer Science", "Year": 1, "Enrollment Date": (today + timedelta(days=365)).strftime("%Y-%m-%d"), "Email": "future@uni.edu"},  # Future date (rejected)
        {"Student ID": "STU3005", "Full Name": "Liam Wilson", "Sex": "boy", "Dept": "BUS", "Program": "Business Administration", "Year": "two", "Enrollment Date": "2023-09-01", "Email": "liam.w@uni.edu"},  # Non-numeric year
        {"Student ID": "   ", "Full Name": None, "Sex": None, "Dept": None, "Program": None, "Year": None, "Enrollment Date": None, "Email": None},  # Empty row
    ]
    pd.DataFrame(students_messy_data).to_excel(os.path.join(SAMPLE_DATA_DIR, "students_messy.xlsx"), index=False)

    # ----------------- 2. COURSES -----------------
    courses_clean_data = [
        {"course_code": "CS101", "title": "Introduction to Computer Science", "credits": 3, "department": "CS"},
        {"course_code": "CS202", "title": "Data Structures & Algorithms", "credits": 4, "department": "CS"},
        {"course_code": "ENG101", "title": "Engineering Mechanics", "credits": 3, "department": "ENG"},
        {"course_code": "BUS101", "title": "Principles of Accounting", "credits": 3, "department": "BUS"},
    ]
    pd.DataFrame(courses_clean_data).to_excel(os.path.join(SAMPLE_DATA_DIR, "courses_clean.xlsx"), index=False)

    # Deliberately messy courses
    # Tests: header alias ('Code', 'Course Title'), lowercase code, duplicate, invalid credits, missing code
    courses_messy_data = [
        {"Code": "cs401", "Course Title": "  artificial intelligence  ", "Credits": 3, "Dept": "cs"},
        {"Code": "CS401", "Course Title": "Artificial Intelligence", "Credits": 3, "Dept": "CS"},  # Duplicate
        {"Code": "ENG305", "Course Title": "Fluid Dynamics", "Credits": 99, "Dept": "eng"},  # Credits out of range (defaulted to 3)
        {"Code": "", "Course Title": "Mystery Course", "Credits": 3, "Dept": "CS"},  # Missing code (rejected)
        {"Code": "BUS310", "Course Title": "", "Credits": "four", "Dept": "bus"},  # Missing title & non-numeric credits
    ]
    pd.DataFrame(courses_messy_data).to_excel(os.path.join(SAMPLE_DATA_DIR, "courses_messy.xlsx"), index=False)

    # ----------------- 3. GRADES -----------------
    grades_clean_data = [
        {"student_id": "STU1001", "course_code": "CS101", "semester": "2024-Fall", "score": 95.0},
        {"student_id": "STU1002", "course_code": "CS101", "semester": "2024-Fall", "score": 82.5},
        {"student_id": "STU1003", "course_code": "CS101", "semester": "2024-Fall", "score": 76.0},
        {"student_id": "STU1004", "course_code": "ENG101", "semester": "2024-Fall", "score": 89.0},
    ]
    pd.DataFrame(grades_clean_data).to_excel(os.path.join(SAMPLE_DATA_DIR, "grades_clean.xlsx"), index=False)

    # Deliberately messy grades
    # Tests: score 105 (rejected), unknown student_id (rejected), unknown course (rejected), negative score (rejected), non-numeric score (rejected)
    grades_messy_data = [
        {"student_id": "STU1001", "course_code": "CS101", "semester": "2024-Fall", "score": 105.0},  # Score > 100 (rejected)
        {"student_id": "STU9999", "course_code": "CS101", "semester": "2024-Fall", "score": 85.0},   # Unknown student (rejected)
        {"student_id": "STU1002", "course_code": "NONEXISTENT", "semester": "2024-Fall", "score": 75.0},  # Unknown course (rejected)
        {"student_id": "STU1003", "course_code": "CS101", "semester": "2024-Fall", "score": -10.0},  # Score < 0 (rejected)
        {"student_id": "STU1004", "course_code": "ENG101", "semester": "2024-Fall", "score": "A+"},   # Non-numeric score (rejected)
        {"student_id": "STU1001", "course_code": "CS202", "semester": "2024-Fall", "score": 88.0},   # Valid
        {"student_id": "STU1001", "course_code": "CS202", "semester": "2024-Fall", "score": 88.0},   # Duplicate (removed)
    ]
    pd.DataFrame(grades_messy_data).to_excel(os.path.join(SAMPLE_DATA_DIR, "grades_messy.xlsx"), index=False)

    # ----------------- 4. ATTENDANCE -----------------
    attendance_clean_data = [
        {"student_id": "STU1001", "course_code": "CS101", "date": (today - timedelta(days=2)).strftime("%Y-%m-%d"), "status": "P"},
        {"student_id": "STU1002", "course_code": "CS101", "date": (today - timedelta(days=2)).strftime("%Y-%m-%d"), "status": "A"},
        {"student_id": "STU1003", "course_code": "CS101", "date": (today - timedelta(days=2)).strftime("%Y-%m-%d"), "status": "L"},
    ]
    pd.DataFrame(attendance_clean_data).to_excel(os.path.join(SAMPLE_DATA_DIR, "attendance_clean.xlsx"), index=False)

    # Deliberately messy attendance
    # Tests: status variations ('present', '1', 'absent', '0', 'late'), future date, unknown status, unknown student
    attendance_messy_data = [
        {"student_id": "STU1001", "course_code": "CS101", "date": (today - timedelta(days=3)).strftime("%Y-%m-%d"), "status": "present"},  # Standardized to P
        {"student_id": "STU1002", "course_code": "CS101", "date": (today - timedelta(days=3)).strftime("%Y-%m-%d"), "status": "0"},        # Standardized to A
        {"student_id": "STU1003", "course_code": "CS101", "date": (today - timedelta(days=3)).strftime("%Y-%m-%d"), "status": "Tardy"},    # Standardized to L
        {"student_id": "STU1001", "course_code": "CS101", "date": (today + timedelta(days=10)).strftime("%Y-%m-%d"), "status": "P"},       # Future date (rejected)
        {"student_id": "STU1001", "course_code": "CS101", "date": (today - timedelta(days=4)).strftime("%Y-%m-%d"), "status": "Excused"},  # Invalid status (rejected)
        {"student_id": "STU8888", "course_code": "CS101", "date": (today - timedelta(days=4)).strftime("%Y-%m-%d"), "status": "P"},        # Unknown student (rejected)
    ]
    pd.DataFrame(attendance_messy_data).to_excel(os.path.join(SAMPLE_DATA_DIR, "attendance_messy.xlsx"), index=False)

    print("Successfully generated all 8 sample Excel files (4 clean + 4 messy) in sample_data/!")

if __name__ == '__main__':
    create_sample_files()
