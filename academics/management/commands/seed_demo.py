from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import Profile, Role
from academics.models import Department, Program, Course, Student, Enrollment, Attendance
from uploads.models import Upload, UploadStatus

class Command(BaseCommand):
    help = 'Seeds initial departments, programs, demo users with roles, and sample data.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding demo data..."))

        # 1. Departments
        departments_data = [
            ('CS', 'Computer Science & Engineering'),
            ('ENG', 'Mechanical & Civil Engineering'),
            ('BUS', 'Business Administration'),
            ('MED', 'School of Medicine'),
        ]
        dept_objs = {}
        for code, name in departments_data:
            dept, _ = Department.objects.get_or_create(code=code, defaults={'name': name})
            dept_objs[code] = dept
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(dept_objs)} departments."))

        # 2. Programs
        programs_data = [
            ('CS', 'Bachelor of Computer Science', 4),
            ('CS', 'Bachelor of Software Engineering', 4),
            ('ENG', 'Bachelor of Mechanical Engineering', 4),
            ('ENG', 'Bachelor of Electrical Engineering', 4),
            ('BUS', 'Bachelor of Business Administration', 3),
        ]
        prog_objs = {}
        for dept_code, name, duration in programs_data:
            prog, _ = Program.objects.get_or_create(
                department=dept_objs[dept_code],
                name=name,
                defaults={'duration_years': duration}
            )
            prog_objs[(dept_code, name)] = prog
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(prog_objs)} programs."))

        # 3. Courses
        courses_data = [
            ('CS101', 'Introduction to Computer Science', 3, 'CS'),
            ('CS202', 'Data Structures & Algorithms', 4, 'CS'),
            ('CS305', 'Database Management Systems', 3, 'CS'),
            ('ENG101', 'Engineering Mechanics', 3, 'ENG'),
            ('ENG201', 'Thermodynamics I', 4, 'ENG'),
            ('BUS101', 'Principles of Accounting', 3, 'BUS'),
            ('BUS205', 'Marketing Fundamentals', 3, 'BUS'),
        ]
        course_objs = {}
        for code, title, credits, dept_code in courses_data:
            c, _ = Course.objects.get_or_create(
                code=code,
                defaults={
                    'title': title,
                    'credits': credits,
                    'department': dept_objs[dept_code]
                }
            )
            course_objs[code] = c
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(course_objs)} courses."))

        # 4. Users with Roles
        users_config = [
            ('admin', 'admin@university.edu', Role.ADMIN, None, True),
            ('registrar', 'registrar@university.edu', Role.REGISTRAR, None, False),
            ('dept_head', 'head.cs@university.edu', Role.DEPT_HEAD, dept_objs['CS'], False),
            ('student', 'student@university.edu', Role.STUDENT, dept_objs['CS'], False),
        ]

        user_objs = {}
        for username, email, role, dept, is_super in users_config:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'is_staff': is_super or (role in (Role.ADMIN, Role.REGISTRAR)),
                    'is_superuser': is_super
                }
            )
            user.set_password('Password123!')
            user.save()

            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = role
            profile.department = dept
            profile.save()
            user_objs[username] = user
        self.stdout.write(self.style.SUCCESS("Seeded 4 demo users (admin, registrar, dept_head, student) with password 'Password123!'."))

        # 5. Seed Students
        students_data = [
            ('STU1001', 'Alice Johnson', 'Female', ('CS', 'Bachelor of Computer Science'), 2, '2023-09-01', 'alice.j@university.edu'),
            ('STU1002', 'Bob Smith', 'Male', ('CS', 'Bachelor of Computer Science'), 2, '2023-09-01', 'bob.s@university.edu'),
            ('STU1003', 'Charlie Davis', 'Male', ('CS', 'Bachelor of Software Engineering'), 1, '2024-09-01', 'charlie.d@university.edu'),
            ('STU1004', 'Diana Prince', 'Female', ('ENG', 'Bachelor of Mechanical Engineering'), 3, '2022-09-01', 'diana.p@university.edu'),
            ('STU1005', 'Evan Wright', 'Male', ('ENG', 'Bachelor of Electrical Engineering'), 1, '2024-09-01', 'evan.w@university.edu'),
            ('STU1006', 'Fiona Gallagher', 'Female', ('BUS', 'Bachelor of Business Administration'), 2, '2023-09-01', 'fiona.g@university.edu'),
            ('STU1007', 'George Clark', 'Male', ('BUS', 'Bachelor of Business Administration'), 3, '2022-09-01', 'george.c@university.edu'),
            ('STU1008', 'Hannah Abbott', 'Female', ('CS', 'Bachelor of Software Engineering'), 4, '2021-09-01', 'hannah.a@university.edu'),
        ]

        stu_objs = {}
        for sid, name, gender, prog_key, year, enrol_date, email in students_data:
            prog = prog_objs[prog_key]
            stu, _ = Student.objects.get_or_create(
                student_id=sid,
                defaults={
                    'name': name,
                    'gender': gender,
                    'program': prog,
                    'year': year,
                    'enrollment_date': enrol_date,
                    'email': email,
                }
            )
            stu_objs[sid] = stu

        # Link demo student account to STU1001
        student_user = user_objs['student']
        student_user.profile.student_record = stu_objs['STU1001']
        student_user.profile.save()
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(stu_objs)} students."))

        # 6. Seed Enrollments & Grades
        grades_data = [
            ('STU1001', 'CS101', '2024-Fall', 92.5, 'A'),
            ('STU1001', 'CS202', '2024-Fall', 84.0, 'B'),
            ('STU1002', 'CS101', '2024-Fall', 78.5, 'C'),
            ('STU1002', 'CS202', '2024-Fall', 48.0, 'F'),
            ('STU1003', 'CS101', '2024-Fall', 88.0, 'B'),
            ('STU1004', 'ENG101', '2024-Fall', 95.0, 'A'),
            ('STU1004', 'ENG201', '2024-Fall', 89.0, 'B'),
            ('STU1005', 'ENG101', '2024-Fall', 62.0, 'D'),
            ('STU1006', 'BUS101', '2024-Fall', 85.0, 'B'),
            ('STU1007', 'BUS101', '2024-Fall', 71.0, 'C'),
            ('STU1008', 'CS305', '2024-Fall', 91.0, 'A'),
        ]
        for sid, ccode, sem, score, grade in grades_data:
            Enrollment.objects.get_or_create(
                student=stu_objs[sid],
                course=course_objs[ccode],
                semester=sem,
                defaults={'score': score, 'grade_letter': grade}
            )
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(grades_data)} course enrollments & grades."))

        # 7. Seed Attendance Records
        today = date.today()
        attendance_data = [
            ('STU1001', 'CS101', today - timedelta(days=5), 'P'),
            ('STU1001', 'CS101', today - timedelta(days=3), 'P'),
            ('STU1001', 'CS101', today - timedelta(days=1), 'L'),
            ('STU1002', 'CS101', today - timedelta(days=5), 'P'),
            ('STU1002', 'CS101', today - timedelta(days=3), 'A'),
            ('STU1002', 'CS101', today - timedelta(days=1), 'P'),
            ('STU1004', 'ENG101', today - timedelta(days=4), 'P'),
            ('STU1004', 'ENG101', today - timedelta(days=2), 'P'),
        ]
        for sid, ccode, att_date, status in attendance_data:
            Attendance.objects.get_or_create(
                student=stu_objs[sid],
                course=course_objs[ccode],
                date=att_date,
                defaults={'status': status}
            )
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(attendance_data)} attendance records."))
        self.stdout.write(self.style.SUCCESS("Demo database successfully primed!"))
