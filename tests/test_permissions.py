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
