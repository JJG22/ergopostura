#!/bin/sh
set -e

# Render define RENDER=true. Sin estas variables Django arrancaria con la configuracion
# de desarrollo y fallaria con un error confuso sobre POSTGRES_DB.
if [ -n "$RENDER" ]; then
  missing=""
  case "$DJANGO_SETTINGS_MODULE" in *prod*) ;; *) missing="$missing DJANGO_SETTINGS_MODULE=config.settings.prod" ;; esac
  [ -n "$DATABASE_URL" ] || missing="$missing DATABASE_URL"
  [ -n "$DJANGO_SECRET_KEY" ] || missing="$missing DJANGO_SECRET_KEY"
  if [ -n "$missing" ]; then
    echo "ERROR: faltan variables de entorno en Render:$missing" >&2
    echo "Agregalas en el servicio, pestana Environment, y vuelve a desplegar." >&2
    exit 1
  fi
fi

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
