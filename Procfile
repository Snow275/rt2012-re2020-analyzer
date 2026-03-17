web: python manage.py migrate --fake-initial && python manage.py collectstatic --noinput && python manage.py create_superuser_if_missing && gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT
