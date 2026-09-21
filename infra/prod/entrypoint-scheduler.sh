#!/bin/sh
# Production Celery beat: schedules every module's declared periodic job.
set -eu
cd /app
exec celery -A config.celery beat --loglevel=INFO --schedule=/tmp/celerybeat-schedule
