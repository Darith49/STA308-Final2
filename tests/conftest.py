import pytest
from datetime import date
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from accounts.models import Profile, Role
from academics.models import Department, Program, Course, Student, Enrollment, Attendance

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def dept_cs(db):
    dept, _ = Department.objects.get_or_create(code='CS', defaults={'name': 'Computer Science'})
    return dept

@pytest.fixture
def dept_eng(db):
    dept, _ = Department.objects.get_or_create(code='ENG', defaults={'name': 'Engineering'})
    return dept

@pytest.fixture
def program_cs(db, dept_cs):
    prog, _ = Program.objects.get_or_create(department=dept_cs, name='Computer Science', defaults={'duration_years': 4})
    return prog

@pytest.fixture
def course_cs101(db, dept_cs):
    c, _ = Course.objects.get_or_create(code='CS101', defaults={'title': 'Intro to CS', 'credits': 3, 'department': dept_cs})
    return c

@pytest.fixture
def student_stu1(db, program_cs):
    s, _ = Student.objects.get_or_create(
        student_id='STU1001',
        defaults={
            'name': 'Alice Test',
            'gender': 'Female',
            'program': program_cs,
            'year': 2,
            'enrollment_date': date(2023, 9, 1),
            'email': 'alice@test.edu'
        }
    )
    return s

@pytest.fixture
def admin_user(db):
    u, _ = User.objects.get_or_create(username='test_admin', defaults={'is_superuser': True, 'is_staff': True})
    u.set_password('Password123!')
    u.save()
    u.profile.role = Role.ADMIN
    u.profile.save()
    return u

@pytest.fixture
def registrar_user(db):
    u, _ = User.objects.get_or_create(username='test_registrar', defaults={'is_staff': True})
    u.set_password('Password123!')
    u.save()
    u.profile.role = Role.REGISTRAR
    u.profile.save()
    return u

@pytest.fixture
def dept_head_user(db, dept_cs):
    u, _ = User.objects.get_or_create(username='test_depthead', defaults={'is_staff': False})
    u.set_password('Password123!')
    u.save()
    u.profile.role = Role.DEPT_HEAD
    u.profile.department = dept_cs
    u.profile.save()
    return u

@pytest.fixture
def student_user(db, student_stu1):
    u, _ = User.objects.get_or_create(username='test_student', defaults={'is_staff': False})
    u.set_password('Password123!')
    u.save()
    u.profile.role = Role.STUDENT
    u.profile.student_record = student_stu1
    u.profile.save()
    return u
