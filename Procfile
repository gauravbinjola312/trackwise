web: gunicorn trackwise_backend.wsgi:application --workers 4 --worker-class gthread --threads 2 --bind 0.0.0.0:$PORT --timeout 30 --keep-alive 5 --max-requests 1000 --max-requests-jitter 100 --log-level info --access-logfile - --error-logfile -
worker: celery -A trackwise_backend worker --loglevel=info --concurrency=2
