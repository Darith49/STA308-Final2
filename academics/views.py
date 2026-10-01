import csv
from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import TemplateView, ListView
from django.db.models import Avg, Count, Q

from accounts.permissions import RoleRequiredMixin
from accounts.models import Role
from analytics.scoping import scope_for
from .models import Department, Program, Course, Student, Enrollment, Attendance

def sanitize_csv_cell(val):
    """Prevent CSV formula injection by prefixing unsafe characters."""
    if val is None:
        return ""
    s = str(val)
    if s.startswith(('=', '+', '-', '@', '\t', '\r')):
        return f"'{s}"
    return s

class DashboardView(TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        profile = getattr(user, 'profile', None)

        ctx['departments'] = Department.objects.all().order_by('code')
        ctx['semesters'] = (
            Enrollment.objects.values_list('semester', flat=True)
            .distinct()
            .order_by('-semester')
        )
        ctx['courses'] = (
            scope_for(user, Course.objects.all(), dept_field='department')
            .order_by('code')
        )

        # Scoped recent activity for dashboard table
        if profile and profile.is_student:
            ctx['student_enrollments'] = (
                Enrollment.objects.filter(student=profile.student_record)
                .select_related('course')
                .order_by('-semester')
            )
            ctx['student_attendance'] = (
                Attendance.objects.filter(student=profile.student_record)
                .select_related('course')
                .order_by('-date')[:10]
            )
        return ctx


class StudentListView(ListView):
    model = Student
    template_name = 'records/students_list.html'
    context_object_name = 'students'
    paginate_by = 25

    def get_queryset(self):
        user = self.request.user
        qs = scope_for(user, Student.objects.all(), dept_field='program__department')
        qs = qs.select_related('program', 'program__department').order_by('student_id')

        q = self.request.GET.get('q', '').strip()
        dept = self.request.GET.get('dept', '').strip()
        year = self.request.GET.get('year', '').strip()

        if q:
            qs = qs.filter(Q(student_id__icontains=q) | Q(name__icontains=q) | Q(email__icontains=q))
        if dept and (user.profile.is_admin or user.profile.is_registrar):
            qs = qs.filter(program__department__code__iexact=dept)
        if year:
            qs = qs.filter(year=year)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['departments'] = Department.objects.all().order_by('code')
        ctx['search_query'] = self.request.GET.get('q', '')
        ctx['selected_dept'] = self.request.GET.get('dept', '')
        ctx['selected_year'] = self.request.GET.get('year', '')
        return ctx


class StudentExportCsvView(ListView):
    def get(self, request, *args, **kwargs):
        user = request.user
        qs = scope_for(user, Student.objects.all(), dept_field='program__department')
        qs = qs.select_related('program', 'program__department').order_by('student_id')

        q = request.GET.get('q', '').strip()
        dept = request.GET.get('dept', '').strip()
        year = request.GET.get('year', '').strip()

        if q:
            qs = qs.filter(Q(student_id__icontains=q) | Q(name__icontains=q) | Q(email__icontains=q))
        if dept and (user.profile.is_admin or user.profile.is_registrar):
            qs = qs.filter(program__department__code__iexact=dept)
        if year:
            qs = qs.filter(year=year)

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="students_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['Student ID', 'Name', 'Gender', 'Department', 'Program', 'Year', 'Enrollment Date', 'Email'])

        for s in qs:
            dept_code = s.program.department.code if (s.program and s.program.department) else ''
            prog_name = s.program.name if s.program else ''
            writer.writerow([
                sanitize_csv_cell(s.student_id),
                sanitize_csv_cell(s.name),
                sanitize_csv_cell(s.gender),
                sanitize_csv_cell(dept_code),
                sanitize_csv_cell(prog_name),
                sanitize_csv_cell(s.year),
                sanitize_csv_cell(s.enrollment_date),
                sanitize_csv_cell(s.email),
            ])
        return response


class CourseListView(ListView):
    model = Course
    template_name = 'records/courses_list.html'
    context_object_name = 'courses'
    paginate_by = 25

    def get_queryset(self):
        user = self.request.user
        qs = scope_for(user, Course.objects.all(), dept_field='department')
        qs = qs.select_related('department').annotate(student_count=Count('enrollments')).order_by('code')

        q = self.request.GET.get('q', '').strip()
        dept = self.request.GET.get('dept', '').strip()

        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(title__icontains=q))
        if dept and (user.profile.is_admin or user.profile.is_registrar):
            qs = qs.filter(department__code__iexact=dept)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['departments'] = Department.objects.all().order_by('code')
        ctx['search_query'] = self.request.GET.get('q', '')
        ctx['selected_dept'] = self.request.GET.get('dept', '')
        return ctx


class EnrollmentListView(ListView):
    model = Enrollment
    template_name = 'records/grades_list.html'
    context_object_name = 'enrollments'
    paginate_by = 30

    def get_queryset(self):
        user = self.request.user
        qs = scope_for(user, Enrollment.objects.all(), dept_field='course__department')
        qs = qs.select_related('student', 'course', 'course__department').order_by('-semester', 'student__student_id')

        q = self.request.GET.get('q', '').strip()
        sem = self.request.GET.get('semester', '').strip()
        grade = self.request.GET.get('grade', '').strip()
        course_code = self.request.GET.get('course', '').strip()

        if q:
            qs = qs.filter(Q(student__student_id__icontains=q) | Q(student__name__icontains=q) | Q(course__code__icontains=q))
        if sem:
            qs = qs.filter(semester=sem)
        if grade:
            qs = qs.filter(grade_letter=grade)
        if course_code:
            qs = qs.filter(course__code__iexact=course_code)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['semesters'] = Enrollment.objects.values_list('semester', flat=True).distinct().order_by('-semester')
        ctx['grade_letters'] = ['A', 'B', 'C', 'D', 'F']
        ctx['search_query'] = self.request.GET.get('q', '')
        ctx['selected_sem'] = self.request.GET.get('semester', '')
        ctx['selected_grade'] = self.request.GET.get('grade', '')
        return ctx


class EnrollmentExportCsvView(ListView):
    def get(self, request, *args, **kwargs):
        user = request.user
        qs = scope_for(user, Enrollment.objects.all(), dept_field='course__department')
        qs = qs.select_related('student', 'course', 'course__department').order_by('-semester', 'student__student_id')

        q = request.GET.get('q', '').strip()
        sem = request.GET.get('semester', '').strip()
        grade = request.GET.get('grade', '').strip()

        if q:
            qs = qs.filter(Q(student__student_id__icontains=q) | Q(student__name__icontains=q) | Q(course__code__icontains=q))
        if sem:
            qs = qs.filter(semester=sem)
        if grade:
            qs = qs.filter(grade_letter=grade)

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="grades_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['Student ID', 'Student Name', 'Course Code', 'Course Title', 'Semester', 'Score', 'Grade Letter'])

        for e in qs:
            writer.writerow([
                sanitize_csv_cell(e.student.student_id),
                sanitize_csv_cell(e.student.name),
                sanitize_csv_cell(e.course.code),
                sanitize_csv_cell(e.course.title),
                sanitize_csv_cell(e.semester),
                sanitize_csv_cell(e.score),
                sanitize_csv_cell(e.grade_letter),
            ])
        return response


class AttendanceListView(ListView):
    model = Attendance
    template_name = 'records/attendance_list.html'
    context_object_name = 'attendances'
    paginate_by = 30

    def get_queryset(self):
        user = self.request.user
        qs = scope_for(user, Attendance.objects.all(), dept_field='course__department')
        qs = qs.select_related('student', 'course', 'course__department').order_by('-date', 'course__code')

        q = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()
        course_code = self.request.GET.get('course', '').strip()

        if q:
            qs = qs.filter(Q(student__student_id__icontains=q) | Q(student__name__icontains=q) | Q(course__code__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if course_code:
            qs = qs.filter(course__code__iexact=course_code)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = Attendance.STATUS_CHOICES
        ctx['courses'] = scope_for(self.request.user, Course.objects.all(), dept_field='department').order_by('code')
        ctx['search_query'] = self.request.GET.get('q', '')
        ctx['selected_status'] = self.request.GET.get('status', '')
        ctx['selected_course'] = self.request.GET.get('course', '')
        return ctx
