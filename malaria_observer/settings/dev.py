from .base import *
from .logging_config import LOGGING

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

LOGGING = LOGGING.copy()
LOGGING["root"] = LOGGING["root"].copy()
LOGGING["root"]["handlers"] = ["console"]
LOGGING["root"]["level"] = "DEBUG"

try:
    from .local import *
except ImportError:
    pass
