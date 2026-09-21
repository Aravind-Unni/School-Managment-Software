#!/bin/sh
# Production API entrypoint: ensure object bucket, migrate, then gunicorn.
set -eu
cd /app
python - <<'PY'
"""Create the private object-storage bucket if it does not exist."""
import os
import boto3
from botocore.exceptions import ClientError

endpoint = os.environ["OBJECT_STORAGE_ENDPOINT"]
bucket = os.environ["OBJECT_STORAGE_BUCKET"]
client = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=os.environ["OBJECT_STORAGE_ACCESS_KEY"],
    aws_secret_access_key=os.environ["OBJECT_STORAGE_SECRET_KEY"],
)
try:
    client.head_bucket(Bucket=bucket)
except ClientError:
    client.create_bucket(Bucket=bucket)
print(f"object bucket ready: {bucket}")
PY
python backend/manage.py migrate --noinput
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout 60 \
  --access-logfile - \
  --error-logfile -
