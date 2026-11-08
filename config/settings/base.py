"""Configuracion comun a todos los entornos."""
import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def required_env(name: str) -> str:
    """Falla al arrancar si falta una variable, en vez de usar un valor inseguro."""
    value = os.environ.get(name)
    if not value:
        raise ImproperlyConfigured(f"Falta la variable de entorno {name}.")
    return value


def list_env(name: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
    "apps.accounts",
    "apps.geography",
    "apps.companies",
    "apps.contracts",
    "apps.visits",
    "apps.evaluations",
    "apps.indicators",
    "apps.tasks",
    "apps.dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.accounts.middleware.PasswordChangeRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.navigation",
            ],
        },
    },
]

# utf8mb4 guarda todo el texto (tildes, ñ, emojis). El modo estricto hace que MySQL rechace
# un dato invalido en vez de recortarlo sin avisar.
MYSQL_OPTIONS = {"charset": "utf8mb4", "init_command": "SET sql_mode='STRICT_TRANS_TABLES'"}

if os.environ.get("DATABASE_URL"):
    # En produccion el proveedor entrega la conexion como una sola URL.
    default_database = dj_database_url.parse(
        os.environ["DATABASE_URL"], conn_max_age=60, conn_health_checks=True
    )
    options = default_database.setdefault("OPTIONS", {})
    # Aiven la entrega con ?ssl-mode=REQUIRED; el conector espera llamarlo ssl_mode.
    if "ssl-mode" in options:
        options["ssl_mode"] = options.pop("ssl-mode")
    options.update(MYSQL_OPTIONS)
    DATABASES = {"default": default_database}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": required_env("MYSQL_DATABASE"),
            "USER": required_env("MYSQL_USER"),
            "PASSWORD": required_env("MYSQL_PASSWORD"),
            "HOST": os.environ.get("MYSQL_HOST", "localhost"),
            "PORT": os.environ.get("MYSQL_PORT", "3306"),
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": MYSQL_OPTIONS,
        }
    }

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "accounts:login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Lectura de contratos con Claude. Sin la clave, el modulo de contratos funciona sin IA.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CONTRACT_AI_MODEL = os.environ.get("CONTRACT_AI_MODEL", "claude-opus-5-5")

# Sin marcar "Recordarme" la sesion termina al cerrar el navegador.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"
