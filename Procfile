web: gunicorn sms.wsgi:application --bind 0.0.0.0:$PORT
worker: celery -A sms worker -l info
beat: celery -A sms beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
