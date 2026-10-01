from django.contrib import admin
from .models import Department, Program, Course, Student, Enrollment, Attendance

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'created_at')
    search_fields = ('code', 'name')


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'duration_years')
    list_filter = ('department',)
    search_fields = ('name',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'credits', 'department')
    list_filter = ('department', 'credits')
    search_fields = ('code', 'title')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'name', 'gender', 'program', 'year', 'enrollment_date')
    list_filter = ('gender', 'year', 'program__department')
    search_fields = ('student_id', 'name', 'email')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'semester', 'score', 'grade_letter')
    list_filter = ('semester', 'grade_letter', 'course__department')
    search_fields = ('student__student_id', 'student__name', 'course__code')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'date', 'status')
    list_filter = ('status', 'date', 'course__department')
    search_fields = ('student__student_id', 'course__code')
