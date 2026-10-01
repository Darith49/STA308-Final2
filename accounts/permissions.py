from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import AccessMixin
from rest_framework.permissions import BasePermission
from .models import Role

def role_required(allowed_roles):
    """
    Decorator for views that checks whether a user has one of the allowed roles.
    allowed_roles: list or tuple of role strings, e.g. [Role.ADMIN, Role.REGISTRAR]
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            
            profile = getattr(request.user, 'profile', None)
            if not profile:
                raise PermissionDenied("User has no assigned profile/role.")
            
            if request.user.is_superuser or profile.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            raise PermissionDenied(f"Access denied. Role '{profile.get_role_display()}' is not authorized.")
        return _wrapped_view
    return decorator


class RoleRequiredMixin(AccessMixin):
    """
    CBV mixin that verifies that the current user has one of the allowed roles.
    """
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        profile = getattr(request.user, 'profile', None)
        if not profile:
            raise PermissionDenied("User has no assigned profile/role.")
        
        if request.user.is_superuser or profile.role in self.allowed_roles:
            return super().dispatch(request, *args, **kwargs)
        
        raise PermissionDenied(f"Access denied. Role '{profile.get_role_display()}' is not authorized.")


# DRF Permissions
class HasRolePermission(BasePermission):
    allowed_roles = []

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True
        profile = getattr(request.user, 'profile', None)
        return bool(profile and profile.role in self.allowed_roles)


class IsAdminUserOrRole(HasRolePermission):
    allowed_roles = [Role.ADMIN]


class CanUploadPermission(HasRolePermission):
    allowed_roles = [Role.ADMIN, Role.REGISTRAR]
