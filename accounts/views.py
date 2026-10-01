from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView as BaseLoginView, LogoutView as BaseLogoutView, PasswordChangeView as BasePasswordChangeView
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, TemplateView
from .models import Profile, Role
from .permissions import RoleRequiredMixin
from .forms import UserAdminCreateForm, UserAdminUpdateForm
from uploads.models import AuditLog

class CustomLoginView(BaseLoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('dashboard')


class CustomLogoutView(BaseLogoutView):
    next_page = reverse_lazy('accounts:login')


class CustomPasswordChangeView(BasePasswordChangeView):
    template_name = 'registration/password_change_form.html'
    success_url = reverse_lazy('accounts:profile')

    def form_valid(self, form):
        messages.success(self.request, "Your password was updated successfully.")
        return super().form_valid(form)


class ProfileView(TemplateView):
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['user'] = self.request.user
        ctx['profile'] = getattr(self.request.user, 'profile', None)
        return ctx


class UserListView(RoleRequiredMixin, ListView):
    allowed_roles = [Role.ADMIN]
    model = User
    template_name = 'accounts/users_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        qs = User.objects.select_related('profile', 'profile__department').order_by('username')
        q = self.request.GET.get('q', '').strip()
        role = self.request.GET.get('role', '').strip()
        if q:
            qs = qs.filter(username__icontains=q) | qs.filter(email__icontains=q)
        if role:
            qs = qs.filter(profile__role=role)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['roles'] = Role.choices
        ctx['selected_role'] = self.request.GET.get('role', '')
        ctx['search_query'] = self.request.GET.get('q', '')
        return ctx


class UserCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = [Role.ADMIN]
    form_class = UserAdminCreateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        AuditLog.objects.create(
            user=self.request.user,
            action='USER_CREATE',
            target=f"User: {self.object.username}",
            details={'role': self.object.profile.role, 'email': self.object.email}
        )
        messages.success(self.request, f"User '{self.object.username}' created successfully.")
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action_title'] = "Create New User"
        return ctx


class UserUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = [Role.ADMIN]
    model = User
    form_class = UserAdminUpdateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        AuditLog.objects.create(
            user=self.request.user,
            action='USER_UPDATE',
            target=f"User: {self.object.username}",
            details={'role': self.object.profile.role, 'is_active': self.object.is_active}
        )
        messages.success(self.request, f"User '{self.object.username}' updated successfully.")
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action_title'] = f"Edit User: {self.object.username}"
        return ctx


class AuditLogListView(RoleRequiredMixin, ListView):
    allowed_roles = [Role.ADMIN, Role.REGISTRAR]
    model = AuditLog
    template_name = 'accounts/audit_log.html'
    context_object_name = 'logs'
    paginate_by = 30
    ordering = ['-timestamp']

    def get_queryset(self):
        qs = super().get_queryset().select_related('user')
        action = self.request.GET.get('action')
        if action:
            qs = qs.filter(action=action)
        return qs
