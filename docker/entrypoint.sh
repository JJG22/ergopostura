#!/bin/sh
set -e

python manage.py migrate --noinput

case "$DJANGO_SETTINGS_MODULE" in
  *prod*) python manage.py collectstatic --noinput ;;
esac

exec "$@"
