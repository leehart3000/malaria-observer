from .base import *
from .logging_config import LOGGING
from .sentry import init_sentry

DEBUG = False

# ManifestStaticFilesStorage is recommended in production, to prevent
# outdated JavaScript / CSS assets being served from cache
# (e.g. after a Wagtail upgrade).
# See https://docs.djangoproject.com/en/6.0/ref/contrib/staticfiles/#manifeststaticfilesstorage
STORAGES["staticfiles"]["BACKEND"] = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
)

if env("GS_CREDENTIALS_FILE", default=""):
    from google.oauth2 import service_account

    GS_CREDENTIALS = service_account.Credentials.from_service_account_file(
        env("GS_CREDENTIALS_FILE")
    )
else:
    GS_CREDENTIALS = None

STORAGES["default"] = {
    "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
    "OPTIONS": {
        "bucket_name": env("GS_BUCKET_NAME"),
        "project_id": env("GS_PROJECT_ID"),
        "credentials": GS_CREDENTIALS,
        "querystring_auth": False,
        "location": "media",
        "file_overwrite": False,
    },
}

MEDIA_URL = f"https://storage.googleapis.com/{env('GS_BUCKET_NAME')}/media/"

GS_FILE_OVERWRITE = False

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
