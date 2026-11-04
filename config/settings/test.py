from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "solo-para-pruebas"
ALLOWED_HOSTS = ["testserver"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
