from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "solo-para-pruebas"
ALLOWED_HOSTS = ["testserver"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Las pruebas nunca usan claves reales de IA: cada prueba configura la que necesita.
ANTHROPIC_API_KEY = ""
GEMINI_API_KEY = ""
AI_PROVIDER = ""
