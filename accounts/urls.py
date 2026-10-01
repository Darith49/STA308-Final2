from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('password-change/', views.CustomPasswordChangeView.as_view(), name='password_change'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/new/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user_edit'),
    path('audit/', views.AuditLogListView.as_view(), name='audit_log'),
]
