#!/bin/sh
# Prepara la base de datos y los archivos estáticos antes de arrancar Gunicorn.
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
