#!/bin/sh
set -e

python manage.py migrate --noinput

case "$DJANGO_SETTINGS_MODULE" in
  *prod*)
    python manage.py collectstatic --noinput
    # El plan gratis de Render no tiene consola: las cuentas iniciales se crean al arrancar.
    python manage.py ensure_admin
    if [ -n "$DEMO_SEED_PASSWORD" ]; then
      python manage.py seed_demo --allow-production --password "$DEMO_SEED_PASSWORD"
    fi
    ;;
esac

exec "$@"
