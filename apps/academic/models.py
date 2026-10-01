"""
Academic domain models: Department, Program, Course, Student, Grade, and Attendance.
Provides relational data structures linked to Upload records for atomic rollbacks.
"""

from django.db import models
from django.contrib.auth.models import User


def score_to_letter_and_gpa(score: float):
    """Calculate letter grade and 4.0 GPA points from numerical score (0-100)."""
    if score >= 90.0:
        return "A", 4.0, True
    elif score >= 85.0:
        return "B+", 3.5, True
    elif score >= 80.0:
        return "B", 3.0, True
    elif score >= 75.0:
        return "C+", 2.5, True
    elif score >= 70.0:
        return "C", 2.0, True
    elif score >= 60.0:
        return "D", 1.0, True
    else:
        return "F", 0.0, False


class Department(models.Model):
    code = models.CharField(max_length=20, unique=True, help_text="e.g. STAT, CS, MATH")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    head = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_departments",
        help_text="Department head or primary coordinator",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Program(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="programs")
    code = models.CharField(max_length=30, unique=True, help_text="e.g. BS-STAT, MS-DS")
    name = models.CharField(max_length=150)
    degree_level = models.CharField(
        max_length=50,
        choices=[
            ("Undergraduate", "Undergraduate"),
            ("Graduate", "Graduate"),
            ("Postgraduate", "Postgraduate"),
        ],
        default="Undergraduate",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} ({self.name})"


class Course(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="courses")
    program = models.ForeignKey(Program, on_delete=models.SET_NULL, null=True, blank=True, related_name="courses")
    code = models.CharField(max_length=30, unique=True, help_text="e.g. STA308, CS101")
    title = models.CharField(max_length=200)
    credits = models.IntegerField(default=3)
    semester = models.CharField(max_length=50, default="Fall 2026")
    upload = models.ForeignKey(
        "uploads.Upload",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="course_records",
        help_text="Upload record this course was imported from (for rollbacks)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code}: {self.title}"


class Student(models.Model):
    student_id = models.CharField(max_length=30, unique=True, help_text="e.g. STU1001")
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_record",
        help_text="Optional login account for student self-service portal",
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="students")
    program = models.ForeignKey(Program, on_delete=models.SET_NULL, null=True, blank=True, related_name="students")
    cohort = models.CharField(max_length=20, default="2024")
    status = models.CharField(
        max_length=30,
        choices=[("Active", "Active"), ("Graduated", "Graduated"), ("Suspended", "Suspended")],
        default="Active",
    )
    upload = models.ForeignKey(
        "uploads.Upload",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="student_records",
        help_text="Upload record this student was imported from (for rollbacks)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["student_id"]

    def __str__(self):
        return f"{self.student_id} - {self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def current_gpa(self):
        grades = self.grades.all()
        if not grades.exists():
            return 0.0
        total_pts = sum(g.gpa_points for g in grades)
        return round(total_pts / len(grades), 2)

    @property
    def attendance_rate(self):
        records = self.attendance_records.all()
        if not records.exists():
            return 100.0
        attended = records.filter(status__in=["Present", "Late"]).count()
        return round((attended / records.count()) * 100.0, 1)


class Grade(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="grades")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="grades")
    semester = models.CharField(max_length=50, default="Fall 2026")
    numerical_score = models.FloatField()
    letter_grade = models.CharField(max_length=5, blank=True)
    gpa_points = models.FloatField(default=0.0)
    passed = models.BooleanField(default=True)
    upload = models.ForeignKey(
        "uploads.Upload",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="grade_records",
        help_text="Upload record this grade was imported from (for rollbacks)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-semester", "course__code"]
        unique_together = ("student", "course", "semester")

    def save(self, *args, **kwargs):
        letter, pts, is_pass = score_to_letter_and_gpa(self.numerical_score)
        self.letter_grade = letter
        self.gpa_points = pts
        self.passed = is_pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.student_id} | {self.course.code}: {self.numerical_score} ({self.letter_grade})"


class Attendance(models.Model):
    STATUS_CHOICES = [
        ("Present", "Present"),
        ("Absent", "Absent"),
        ("Late", "Late"),
        ("Excused", "Excused"),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attendance_records")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Present")
    session_topic = models.CharField(max_length=200, blank=True)
    upload = models.ForeignKey(
        "uploads.Upload",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attendance_records",
        help_text="Upload record this attendance was imported from (for rollbacks)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "course__code"]

    def __str__(self):
        return f"{self.student.student_id} - {self.course.code} ({self.date}): {self.status}"
