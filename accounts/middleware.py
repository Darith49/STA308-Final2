import re
from django.conf import settings
from django.shortcuts import redirect
from django.urls import resolve

def public_view(view_func):
    """Mark a view function as publicly accessible without login."""
    view_func.is_public = True
    return view_func

class LoginRequiredMiddleware:
    """
    Middleware that ensures all views require authentication by default,
    except paths matching LOGIN_EXEMPT_URLS or marked with @public_view.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        exempt_patterns = getattr(settings, 'LOGIN_EXEMPT_URLS', [])
        self.exempt_regexes = [re.compile(pattern) for pattern in exempt_patterns]

    def __call__(self, request):
        path = request.path_info.lstrip('/')
        
        # Always allow static, media, admin login, and specified exempt URLs
        if request.user.is_authenticated:
            return self.get_response(request)

        # Check path regexes
        if any(regex.match(path) for regex in self.exempt_regexes):
            return self.get_response(request)

        # Check view attribute
        try:
            resolver_match = resolve(request.path_info)
            if getattr(resolver_match.func, 'is_public', False):
                return self.get_response(request)
        except Exception:
            pass

        # Redirect to login URL
        login_url = settings.LOGIN_URL
        # If it's a named route, resolve it
        if not login_url.startswith('/'):
            from django.urls import reverse
            try:
                login_url = reverse(login_url)
            except Exception:
                login_url = '/accounts/login/'

        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path(), login_url=login_url)
