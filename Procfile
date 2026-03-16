web: python manage.py migrate main zero --fake && python manage.py migrate && python manage.py collectstatic --noinput && gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT
