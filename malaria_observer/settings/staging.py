from .base import *
from .logging_config import LOGGING
from .sentry import init_sentry

DEBUG = False

# ManifestStaticFilesStorage is recommended in production, to prevent
# outdated JavaScript / CSS assets being served from cache
# (e.g. after a Wagtail upgrade).
# See https://docs.djangoproject.com/en/6.0/ref/contrib/staticfiles/#manifeststaticfilesstorage
STORAGES["staticfiles"]["BACKEND"] = (
    "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
)

SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    init_sentry(SENTRY_DSN)

LOGGING = LOGGING.copy()
LOGGING["root"] = LOGGING["root"].copy()
LOGGING["root"]["handlers"] = ["json"]
LOGGING["root"]["level"] = "INFO"

try:
    from .local import *
except ImportError:
    pass
