import os

from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "solo-para-desarrollo")
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
# El servidor de desarrollo de Vite (puerto 5173) reenvía /api/ a Django.
CSRF_TRUSTED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
