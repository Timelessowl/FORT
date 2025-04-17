#!/bin/bash

python manage.py makemigrations chat
python manage.py migrate

exec "$@"