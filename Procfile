web: gunicorn taskmanager.wsgi --log-file - --bind 0.0.0.0:$PORT
release: python manage.py migrate --no-input && python manage.py collectstatic --no-input
