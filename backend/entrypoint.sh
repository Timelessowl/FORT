#!/bin/bash

python manage.py makemigrations chat
python manage.py makemigrations mermaid
python manage.py migrate

exec "$@"