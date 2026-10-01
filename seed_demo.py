"""
Seed script to create demo users for all 4 roles, departments, programs, courses,
and initial sample datasets.
Usage: python seed_demo.py
"""

import os
import sys
import datetime
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User
from django.core.files import File
from apps.accounts.models import UserProfile, UserRole, log_audit_event
from apps.academic.models import Department, Program, Course, Student, Grade, Attendance
from apps.uploads.models import Upload, UploadStatus, DatasetType
from apps.uploads.tasks import run_pipeline_for_upload
from apps.uploads.templates_generator import generate_dataset_template

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "tests", "fixtures")
os.makedirs(FIXTURES_DIR, exist_ok=True)


def seed():
    print("=" * 60)
    print("Seeding University Data Portal (STA308 Project)")
    print("=" * 60)

    # 1. Setup Academic Departments
    stat_dept, _ = Department.objects.get_or_create(
        code="STAT",
        defaults={
            "name": "Department of Statistics & Data Science",
            "description": "Excellence in statistical modeling, reproducible data science, and analytical research.",
        }
    )
    cs_dept, _ = Department.objects.get_or_create(
        code="CS",
        defaults={
            "name": "Department of Computer Science",
            "description": "Algorithms, software engineering, and artificial intelligence.",
        }
    )
    math_dept, _ = Department.objects.get_or_create(
        code="MATH",
        defaults={
            "name": "Department of Mathematics",
            "description": "Pure and applied mathematics, calculus, and linear algebra.",
        }
    )
    print("-> Departments ready: STAT, CS, MATH")

    # 2. Setup Academic Programs
    bs_stat, _ = Program.objects.get_or_create(
        code="BS-STAT",
        defaults={
            "name": "Bachelor of Science in Statistics & Data Science",
            "department": stat_dept,
            "degree_level": "Undergraduate",
        }
    )
    bs_cs, _ = Program.objects.get_or_create(
        code="BS-CS",
        defaults={
            "name": "Bachelor of Science in Computer Science",
            "department": cs_dept,
            "degree_level": "Undergraduate",
        }
    )
    print("-> Programs ready: BS-STAT, BS-CS")

    # 3. Setup Pre-configured Courses
    sta308, _ = Course.objects.get_or_create(
        code="STA308",
        defaults={
            "title": "Statistical Data Cleaning & Live Dashboards",
            "department": stat_dept,
            "program": bs_stat,
            "credits": 3,
            "semester": "Fall 2026",
        }
    )
    sta302, _ = Course.objects.get_or_create(
        code="STA302",
        defaults={
            "title": "Applied Regression Analysis",
            "department": stat_dept,
            "program": bs_stat,
            "credits": 3,
            "semester": "Fall 2026",
        }
    )
    cs101, _ = Course.objects.get_or_create(
        code="CS101",
        defaults={
            "title": "Introduction to Algorithms & Data Structures",
            "department": cs_dept,
            "program": bs_cs,
            "credits": 4,
            "semester": "Fall 2026",
        }
    )
    print("-> Courses ready: STA308, STA302, CS101")

    # 4. Create Users for all 4 roles
    # Admin
    admin_user, _ = User.objects.get_or_create(
        username="admin_demo",
        defaults={"email": "admin@university.edu", "first_name": "Eleanor", "last_name": "Vance", "is_staff": True}
    )
    admin_user.set_password("password123")
    admin_user.save()
    admin_profile, _ = UserProfile.objects.get_or_create(user=admin_user)
    admin_profile.role = UserRole.ADMIN
    admin_profile.department = "Office of the Vice-Chancellor"
    admin_profile.save()

    # Registrar (Data Owner)
    reg_user, _ = User.objects.get_or_create(
        username="registrar_demo",
        defaults={"email": "registrar@university.edu", "first_name": "Marcus", "last_name": "Brody"}
    )
    reg_user.set_password("password123")
    reg_user.save()
    reg_profile, _ = UserProfile.objects.get_or_create(user=reg_user)
    reg_profile.role = UserRole.REGISTRAR
    reg_profile.department = "Office of Academic Records & Registration"
    reg_profile.save()

    # Department Head (Own Department Read-Only)
    dept_user, _ = User.objects.get_or_create(
        username="depthead_demo",
        defaults={"email": "head.stat@university.edu", "first_name": "Dr. Sarah", "last_name": "Connor"}
    )
    dept_user.set_password("password123")
    dept_user.save()
    dept_profile, _ = UserProfile.objects.get_or_create(user=dept_user)
    dept_profile.role = UserRole.DEPT_HEAD
    dept_profile.department = "Department of Statistics & Data Science"
    dept_profile.save()
    stat_dept.head = dept_user
    stat_dept.save(update_fields=["head"])

    # Student (Stretch Goal)
    student_user, _ = User.objects.get_or_create(
        username="student_demo",
        defaults={"email": "alex.taylor@university.edu", "first_name": "Alex", "last_name": "Taylor"}
    )
    student_user.set_password("password123")
    student_user.save()
    student_profile, _ = UserProfile.objects.get_or_create(user=student_user)
    student_profile.role = UserRole.STUDENT
    student_profile.department = "Department of Statistics & Data Science"
    student_profile.save()

    # Legacy demo analyst
    legacy_user, _ = User.objects.get_or_create(
        username="demo_analyst",
        defaults={"email": "analyst@university.edu", "first_name": "Alex", "last_name": "Taylor"}
    )
    legacy_user.set_password("password123")
    legacy_user.save()
    legacy_profile, _ = UserProfile.objects.get_or_create(user=legacy_user)
    legacy_profile.role = UserRole.ADMIN
    legacy_profile.department = "Department of Statistics & Data Science"
    legacy_profile.save()

    print("-> Demo Accounts Ready:")
    print("   [Admin]           username='admin_demo'      password='password123'")
    print("   [Registrar]       username='registrar_demo'  password='password123'")
    print("   [Department Head] username='depthead_demo'   password='password123'")
    print("   [Student]         username='student_demo'    password='password123'")

    # 5. Create Students
    s1, _ = Student.objects.get_or_create(
        student_id="STU1001",
        defaults={
            "user": student_user,
            "first_name": "Alex",
            "last_name": "Taylor",
            "email": "alex.taylor@university.edu",
            "department": stat_dept,
            "program": bs_stat,
            "cohort": "2024",
            "status": "Active",
        }
    )
    s2, _ = Student.objects.get_or_create(
        student_id="STU1002",
        defaults={
            "first_name": "Jordan",
            "last_name": "Lee",
            "email": "jordan.lee@university.edu",
            "department": stat_dept,
            "program": bs_stat,
            "cohort": "2024",
            "status": "Active",
        }
    )
    s3, _ = Student.objects.get_or_create(
        student_id="STU1003",
        defaults={
            "first_name": "Casey",
            "last_name": "Morgan",
            "email": "casey.morgan@university.edu",
            "department": stat_dept,
            "program": bs_stat,
            "cohort": "2023",
            "status": "Active",
        }
    )
    s4, _ = Student.objects.get_or_create(
        student_id="STU1004",
        defaults={
            "first_name": "Sam",
            "last_name": "Rivera",
            "email": "sam.rivera@university.edu",
            "department": cs_dept,
            "program": bs_cs,
            "cohort": "2024",
            "status": "Active",
        }
    )
    print("-> Students ready: STU1001, STU1002, STU1003, STU1004")

    # 6. Create Grades across semesters (to enable GPA trend for student)
    sample_grades = [
        # Alex Taylor (s1)
        (s1, sta308, "Fall 2026", 92.5),
        (s1, sta302, "Spring 2026", 88.0),
        (s1, cs101, "Fall 2025", 85.0),
        # Jordan Lee (s2)
        (s2, sta308, "Fall 2026", 78.0),
        (s2, sta302, "Spring 2026", 82.5),
        # Casey Morgan (s3)
        (s3, sta308, "Fall 2026", 64.0),
        (s3, sta302, "Spring 2026", 55.0), # Fails
        # Sam Rivera (s4)
        (s4, cs101, "Fall 2026", 94.0),
    ]

    for stu, crs, sem, score in sample_grades:
        Grade.objects.update_or_create(
            student=stu,
            course=crs,
            semester=sem,
            defaults={"numerical_score": score},
        )
    print("-> Grades seeded with multi-semester records.")

    # 7. Create Attendance Records
    base_date = datetime.date(2026, 9, 1)
    for i in range(10):
        session_date = base_date + datetime.timedelta(days=i * 3)
        Attendance.objects.get_or_create(
            student=s1,
            course=sta308,
            date=session_date,
            defaults={"status": "Present" if i != 4 else "Late", "session_topic": f"Session {i+1}: Quality Profiling"}
        )
        Attendance.objects.get_or_create(
            student=s2,
            course=sta308,
            date=session_date,
            defaults={"status": "Present" if i != 2 else "Absent", "session_topic": f"Session {i+1}: Quality Profiling"}
        )
    print("-> Attendance sessions seeded.")

    # 8. Generate starter template files under tests/fixtures/
    for dtype in ["courses", "students", "grades", "attendance"]:
        buf = generate_dataset_template(dtype)
        path = os.path.join(FIXTURES_DIR, f"{dtype}_template.xlsx")
        with open(path, "wb") as f:
            f.write(buf.getvalue())
    print("-> Generated 4 starter template files under tests/fixtures/.")

    # 9. Audit log entry
    log_audit_event(
        admin_user,
        "DEPT_CREATE",
        target_model="Department",
        target_id="STAT",
        details="Seeded initial demo database environment.",
    )
    print("=" * 60)
    print("Seeding complete! Ready for local development.")
    print("=" * 60)


if __name__ == "__main__":
    seed()
