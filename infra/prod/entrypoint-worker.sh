#!/bin/sh
# Production Celery worker entrypoint.
set -eu
cd /app
exec celery -A config.celery worker --loglevel=INFO --concurrency="${CELERY_CONCURRENCY:-2}"
