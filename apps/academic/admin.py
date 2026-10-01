from django.contrib import admin
from apps.academic.models import Department, Program, Course, Student, Grade, Attendance


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "head", "created_at")
    search_fields = ("code", "name")


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "department", "degree_level")
    list_filter = ("department", "degree_level")
    search_fields = ("code", "name")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "department", "program", "credits", "semester")
    list_filter = ("department", "semester")
    search_fields = ("code", "title")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("student_id", "first_name", "last_name", "email", "department", "status")
    list_filter = ("department", "status", "cohort")
    search_fields = ("student_id", "first_name", "last_name", "email")


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "semester", "numerical_score", "letter_grade", "passed")
    list_filter = ("semester", "letter_grade", "passed")
    search_fields = ("student__student_id", "course__code")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "date", "status")
    list_filter = ("status", "date")
    search_fields = ("student__student_id", "course__code")
