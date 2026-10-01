from django.db import models

class Department(models.Model):
    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Program(models.Model):
    name = models.CharField(max_length=150)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='programs')
    duration_years = models.PositiveIntegerField(default=4)

    class Meta:
        unique_together = ('department', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.department.code})"


class Course(models.Model):
    code = models.CharField(max_length=30, unique=True, db_index=True)
    title = models.CharField(max_length=200)
    credits = models.PositiveIntegerField(default=3)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='courses')
    upload = models.ForeignKey('uploads.Upload', on_delete=models.CASCADE, null=True, blank=True, related_name='courses')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.title}"


class Student(models.Model):
    student_id = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    gender = models.CharField(max_length=20, default='Unknown')
    program = models.ForeignKey(Program, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    year = models.PositiveIntegerField(null=True, blank=True)
    enrollment_date = models.DateField(null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    upload = models.ForeignKey('uploads.Upload', on_delete=models.CASCADE, null=True, blank=True, related_name='students')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['student_id']

    def __str__(self):
        return f"{self.student_id} - {self.name}"


class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    semester = models.CharField(max_length=50, db_index=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    grade_letter = models.CharField(max_length=5, blank=True)
    upload = models.ForeignKey('uploads.Upload', on_delete=models.CASCADE, null=True, blank=True, related_name='enrollments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'course', 'semester')
        indexes = [
            models.Index(fields=['course', 'semester']),
        ]
        ordering = ['-semester', 'student__student_id']

    def __str__(self):
        return f"{self.student.student_id} - {self.course.code} ({self.semester}): {self.score}"

    @property
    def is_passing(self):
        return bool(self.score is not None and self.score >= 50)


class Attendance(models.Model):
    STATUS_CHOICES = (
        ('P', 'Present'),
        ('A', 'Absent'),
        ('L', 'Late'),
    )
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=5, choices=STATUS_CHOICES)
    upload = models.ForeignKey('uploads.Upload', on_delete=models.CASCADE, null=True, blank=True, related_name='attendances')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['course', 'date']),
        ]
        ordering = ['-date', 'course__code']

    def __str__(self):
        return f"{self.student.student_id} - {self.course.code} on {self.date}: {self.get_status_display()}"
