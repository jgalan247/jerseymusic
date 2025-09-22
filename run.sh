#!/usr/bin/env bash
set -e
source venv/bin/activate
export DB_NAME=jersey_artwork
export DB_USER=jersey
export DB_PASSWORD=secret
export DB_HOST=/tmp
export DB_PORT=5432
python manage.py migrate
python manage.py runserver
