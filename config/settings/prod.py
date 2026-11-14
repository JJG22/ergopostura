import os
import re

from .base import *  # noqa: F403
from .base import MIDDLEWARE, list_env, required_env

# En desarrollo runserver sirve los estaticos; en produccion los sirve WhiteNoise.
MIDDLEWARE = [MIDDLEWARE[0], "whitenoise.middleware.WhiteNoiseMiddleware", *MIDDLEWARE[1:]]

DEBUG = False
SECRET_KEY = required_env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = list_env("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = list_env("DJANGO_CSRF_TRUSTED_ORIGINS")

# Render publica el dominio del servicio en esta variable.
render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if render_host:
    ALLOWED_HOSTS.append(render_host)
    CSRF_TRUSTED_ORIGINS.append(f"https://{render_host}")

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600
SECURE_CONTENT_TYPE_NOSNIFF = True


# Archivos con huella en el nombre: el navegador los guarda un año y no vuelve a pedirlos.
# Django agrega la huella con 12 caracteres hexadecimales; Vite, con 8 caracteres en assets/.
_HASHED = re.compile(r"\.[0-9a-f]{12}\.[^/]+$")
_VITE_ASSET = re.compile(r"^/static/app/assets/[^/]+-[A-Za-z0-9_-]{8}\.(?:js|css)$")


def WHITENOISE_IMMUTABLE_FILE_TEST(path, url):
    return bool(_HASHED.search(url) or _VITE_ASSET.match(url))
