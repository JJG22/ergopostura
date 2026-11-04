import os

from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "solo-para-desarrollo")
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
