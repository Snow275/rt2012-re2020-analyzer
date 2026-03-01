web: python manage.py migrate && python manage.py create_superuser_if_missing && gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT
