from .base import *
from .logging_config import LOGGING

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-)9kxg106gknn%!4wpmmji-sl2a6+4309d=-*4(p2a)lw419fbl"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

LOGGING = LOGGING.copy()
LOGGING["root"] = LOGGING["root"].copy()
LOGGING["root"]["handlers"] = ["console"]
LOGGING["root"]["level"] = "DEBUG"

try:
    from .local import *
except ImportError:
    pass
