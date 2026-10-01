from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Avg, Case, When, IntegerField, F, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from academics.models import Department, Program, Course, Student, Enrollment, Attendance
from uploads.models import Upload
from .scoping import scope_for

class KpiSummaryApiView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        dept_param = request.GET.get('dept')
        semester_param = request.GET.get('semester')

        # Students query
        stu_qs = scope_for(user, Student.objects.all(), dept_field='program__department')
        if dept_param and (user.profile.is_admin or user.profile.is_registrar):
            stu_qs = stu_qs.filter(program__department__code__iexact=dept_param)
        total_students = stu_qs.count()

        # Courses query
        course_qs = scope_for(user, Course.objects.all(), dept_field='department')
        if dept_param and (user.profile.is_admin or user.profile.is_registrar):
            course_qs = course_qs.filter(department__code__iexact=dept_param)
        total_courses = course_qs.count()

        # Enrollments query
        enr_qs = scope_for(user, Enrollment.objects.all(), dept_field='course__department')
        if dept_param and (user.profile.is_admin or user.profile.is_registrar):
            enr_qs = enr_qs.filter(course__department__code__iexact=dept_param)
        if semester_param:
            enr_qs = enr_qs.filter(semester=semester_param)

        enr_stats = enr_qs.aggregate(
            avg_score=Avg('score'),
            total_count=Count('id'),
            passing_count=Count(Case(When(score__gte=50, then=1), output_field=IntegerField()))
        )
        avg_score = round(enr_stats['avg_score'] or 0.0, 1)
        total_enr = enr_stats['total_count'] or 0
        passing_enr = enr_stats['passing_count'] or 0
        pass_rate = round((passing_enr / total_enr * 100), 1) if total_enr > 0 else 0.0

        # Uploads this month
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        uploads_this_month = Upload.objects.filter(uploaded_at__gte=month_start).count()
        last_upload = Upload.objects.first()
        last_upload_status = last_upload.status if last_upload else 'None'

        return Response({
            'total_students': total_students,
            'total_courses': total_courses,
            'average_score': avg_score,
            'pass_rate': pass_rate,
            'uploads_this_month': uploads_this_month,
            'last_upload_status': last_upload_status,
        })


class StudentsByDepartmentChartApiView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        stu_qs = scope_for(user, Student.objects.all(), dept_field='program__department')

        data = (
            stu_qs.values('program__department__code')
            .annotate(count=Count('id'))
            .order_by('program__department__code')
        )

        labels = [d['program__department__code'] or 'Unassigned' for d in data]
        counts = [d['count'] for d in data]

        return Response({
            'labels': labels,
            'datasets': [{
                'label': 'Students Count',
                'data': counts,
                'backgroundColor': ['#f54e00', '#9fc9a2', '#9fbbe0', '#c0a8dd', '#dfa88f', '#c08532', '#26251e'],
            }]
        })


class YearDistributionChartApiView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        dept_param = request.GET.get('dept')

        stu_qs = scope_for(user, Student.objects.all(), dept_field='program__department')
        if dept_param and (user.profile.is_admin or user.profile.is_registrar):
            stu_qs = stu_qs.filter(program__department__code__iexact=dept_param)

        data = (
            stu_qs.values('year')
            .annotate(count=Count('id'))
            .order_by('year')
        )

        labels = []
        counts = []
        for d in data:
            yr = d['year']
            labels.append(f"Year {yr}" if yr else "Unknown Year")
            counts.append(d['count'])

        return Response({
            'labels': labels,
            'datasets': [{
                'label': 'Students by Year',
                'data': counts,
                'backgroundColor': ['#9fbbe0', '#9fc9a2', '#dfa88f', '#c0a8dd', '#c08532', '#f54e00'],
            }]
        })


class EnrollmentTrendChartApiView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        dept_param = request.GET.get('dept')

        enr_qs = scope_for(user, Enrollment.objects.all(), dept_field='course__department')
        if dept_param and (user.profile.is_admin or user.profile.is_registrar):
            enr_qs = enr_qs.filter(course__department__code__iexact=dept_param)

        data = (
            enr_qs.values('semester')
            .annotate(count=Count('id'))
            .order_by('semester')
        )

        labels = [d['semester'] for d in data]
        counts = [d['count'] for d in data]

        return Response({
            'labels': labels,
            'datasets': [{
                'label': 'Enrollment Volume',
                'data': counts,
                'borderColor': '#f54e00',
                'backgroundColor': 'rgba(245, 78, 0, 0.08)',
                'fill': True,
                'tension': 0.25,
            }]
        })


class GradeDistributionChartApiView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        course_param = request.GET.get('course')
        sem_param = request.GET.get('semester')
        dept_param = request.GET.get('dept')

        enr_qs = scope_for(user, Enrollment.objects.all(), dept_field='course__department')
        if dept_param and (user.profile.is_admin or user.profile.is_registrar):
            enr_qs = enr_qs.filter(course__department__code__iexact=dept_param)
        if course_param:
            enr_qs = enr_qs.filter(course__code__iexact=course_param)
        if sem_param:
            enr_qs = enr_qs.filter(semester=sem_param)

        letter_order = ['A', 'B', 'C', 'D', 'F']
        counts_dict = {ltr: 0 for ltr in letter_order}

        counts = enr_qs.values('grade_letter').annotate(c=Count('id'))
        for item in counts:
            ltr = item['grade_letter']
            if ltr in counts_dict:
                counts_dict[ltr] = item['c']

        return Response({
            'labels': letter_order,
            'datasets': [{
                'label': 'Grades Count',
                'data': [counts_dict[l] for l in letter_order],
                'backgroundColor': ['#1f8a65', '#9fbbe0', '#c08532', '#dfa88f', '#cf2d56'],
            }]
        })


class PassRateByCourseChartApiView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        dept_param = request.GET.get('dept')
        sem_param = request.GET.get('semester')

        enr_qs = scope_for(user, Enrollment.objects.all(), dept_field='course__department')
        if dept_param and (user.profile.is_admin or user.profile.is_registrar):
            enr_qs = enr_qs.filter(course__department__code__iexact=dept_param)
        if sem_param:
            enr_qs = enr_qs.filter(semester=sem_param)

        course_stats = (
            enr_qs.values('course__code')
            .annotate(
                total=Count('id'),
                passed=Count(Case(When(score__gte=50, then=1), output_field=IntegerField()))
            )
            .order_by('course__code')[:15]
        )

        labels = []
        pass_rates = []
        for s in course_stats:
            c_code = s['course__code']
            tot = s['total']
            pas = s['passed']
            rate = round((pas / tot * 100), 1) if tot > 0 else 0
            labels.append(c_code)
            pass_rates.append(rate)

        return Response({
            'labels': labels,
            'datasets': [{
                'label': 'Pass Rate (%)',
                'data': pass_rates,
                'backgroundColor': '#9fc9a2',
                'borderColor': '#7eb682',
                'borderWidth': 1,
            }]
        })


class AttendanceTrendChartApiView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        course_param = request.GET.get('course')
        dept_param = request.GET.get('dept')

        att_qs = scope_for(user, Attendance.objects.all(), dept_field='course__department')
        if dept_param and (user.profile.is_admin or user.profile.is_registrar):
            att_qs = att_qs.filter(course__department__code__iexact=dept_param)
        if course_param:
            att_qs = att_qs.filter(course__code__iexact=course_param)

        daily_stats = (
            att_qs.values('date')
            .annotate(
                total=Count('id'),
                present=Count(Case(When(status='P', then=1), output_field=IntegerField()))
            )
            .order_by('date')[:20]
        )

        labels = [str(s['date']) for s in daily_stats]
        rates = [round((s['present'] / s['total'] * 100), 1) if s['total'] > 0 else 0 for s in daily_stats]

        return Response({
            'labels': labels,
            'datasets': [{
                'label': 'Attendance Rate (%)',
                'data': rates,
                'borderColor': '#26251e',
                'backgroundColor': 'rgba(38, 37, 30, 0.05)',
                'fill': True,
                'tension': 0.25,
            }]
        })
