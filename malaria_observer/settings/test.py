from .base import *

DEBUG = False

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

ALLOWED_HOSTS = ["testserver", "localhost"]

SECRET_KEY = "test-secret-key"