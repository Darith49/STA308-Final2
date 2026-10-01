from .base import *

DEBUG = True

# Disable WhiteNoise in development so Django runserver dynamically serves directly from STATICFILES_DIRS
MIDDLEWARE = [m for m in MIDDLEWARE if 'whitenoise' not in m.lower()]

# In development, use standard static files storage
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Dev auto-login helper for testing when ?autologin=1 is supplied
class DevAutoLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.GET.get('autologin') == '1' and not request.user.is_authenticated:
            from django.contrib.auth import login, get_user_model
            User = get_user_model()
            user = User.objects.filter(is_superuser=True).first() or User.objects.first()
            if user:
                login(request, user)
        return self.get_response(request)

# Insert before LoginRequiredMiddleware
login_req_idx = -1
for i, m in enumerate(MIDDLEWARE):
    if 'LoginRequiredMiddleware' in m:
        login_req_idx = i
        break
if login_req_idx != -1:
    MIDDLEWARE.insert(login_req_idx, 'config.settings.dev.DevAutoLoginMiddleware')
else:
    MIDDLEWARE.append('config.settings.dev.DevAutoLoginMiddleware')

