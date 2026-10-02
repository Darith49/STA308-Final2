import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_dashboard_accessible_to_all_authenticated_roles(client, admin_user, registrar_user, dept_head_user, student_user):
    for u in [admin_user, registrar_user, dept_head_user, student_user]:
        client.force_login(u)
        resp = client.get(reverse('dashboard'))
        assert resp.status_code == 200

@pytest.mark.django_db
def test_upload_view_permissions_matrix(client, admin_user, registrar_user, dept_head_user, student_user):
    upload_url = reverse('uploads:upload_create')
    
    # Admin allowed
    client.force_login(admin_user)
    assert client.get(upload_url).status_code == 200

    # Registrar allowed
    client.force_login(registrar_user)
    assert client.get(upload_url).status_code == 200

    # Dept Head forbidden (403)
    client.force_login(dept_head_user)
    assert client.get(upload_url).status_code == 403

    # Student forbidden (403)
    client.force_login(student_user)
    assert client.get(upload_url).status_code == 403

@pytest.mark.django_db
def test_user_management_permissions_matrix(client, admin_user, registrar_user, dept_head_user, student_user):
    users_url = reverse('accounts:user_list')

    # Admin allowed
    client.force_login(admin_user)
    assert client.get(users_url).status_code == 200

    # Registrar forbidden (403)
    client.force_login(registrar_user)
    assert client.get(users_url).status_code == 403

    # Dept Head forbidden (403)
    client.force_login(dept_head_user)
    assert client.get(users_url).status_code == 403

    # Student forbidden (403)
    client.force_login(student_user)
    assert client.get(users_url).status_code == 403

@pytest.mark.django_db
def test_anonymous_user_redirected_to_login(client):
    resp = client.get(reverse('dashboard'))
    assert resp.status_code == 302
    assert '/accounts/login' in resp.url

@pytest.mark.django_db
def test_seed_demo_assigns_correct_roles():
    from django.core.management import call_command
    from django.contrib.auth.models import User
    from accounts.models import Role

    call_command('seed_demo')

    admin = User.objects.get(username='admin')
    registrar = User.objects.get(username='registrar')
    dept_head = User.objects.get(username='dept_head')
    student = User.objects.get(username='student')

    assert admin.profile.role == Role.ADMIN
    assert registrar.profile.role == Role.REGISTRAR
    assert dept_head.profile.role == Role.DEPT_HEAD
    assert student.profile.role == Role.STUDENT
    assert student.profile.student_record is not None
    assert student.profile.student_record.student_id == 'STU1001'
    assert student.profile.department is None

@pytest.mark.django_db
def test_student_dashboard_and_profile_views(client, student_user):
    client.force_login(student_user)

    resp_dash = client.get(reverse('dashboard'))
    assert resp_dash.status_code == 200
    assert 'student_enrollments' in resp_dash.context
    assert 'student_attendance' in resp_dash.context
    assert resp_dash.context['is_student'] is True

    resp_prof = client.get(reverse('accounts:profile'))
    assert resp_prof.status_code == 200
    assert b'Student' in resp_prof.content
    assert student_user.profile.student_record.student_id.encode() in resp_prof.content
