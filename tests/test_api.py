import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_kpi_api_structure(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    resp = api_client.get(reverse('analytics:api_kpis'))
    assert resp.status_code == 200
    data = resp.json()
    assert 'total_students' in data
    assert 'total_courses' in data
    assert 'average_score' in data
    assert 'pass_rate' in data

@pytest.mark.django_db
def test_chart_api_format(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    chart_endpoints = [
        'analytics:api_chart_students_dept',
        'analytics:api_chart_year_dist',
        'analytics:api_chart_enrollment_trend',
        'analytics:api_chart_grade_dist',
        'analytics:api_chart_pass_rate',
        'analytics:api_chart_attendance_trend',
    ]
    for ep in chart_endpoints:
        resp = api_client.get(reverse(ep))
        assert resp.status_code == 200
        data = resp.json()
        assert 'labels' in data, f"Missing 'labels' in {ep}"
        assert 'datasets' in data, f"Missing 'datasets' in {ep}"
        assert isinstance(data['labels'], list)
        assert isinstance(data['datasets'], list)

@pytest.mark.django_db
def test_upload_status_api(api_client, admin_user):
    from uploads.models import Upload
    api_client.force_authenticate(user=admin_user)
    upload = Upload.objects.create(
        dataset_type='students',
        uploaded_by=admin_user,
        file_hash='abc123status',
        status='done',
        progress_percent=100
    )
    resp = api_client.get(f'/api/uploads/{upload.id}/status/')
    assert resp.status_code == 200
    data = resp.json()
    assert data['id'] == upload.id
    assert data['status'] == 'done'
    assert data['progress'] == 100

