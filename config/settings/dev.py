from .base import *

DEBUG = True

# In development, disable manifest storage if staticfiles haven't been collected
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
