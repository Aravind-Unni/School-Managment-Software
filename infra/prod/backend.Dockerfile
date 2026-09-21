# Production API image: gunicorn, no bind mounts, no runserver.
ARG PYTHON_IMAGE=docker.io/library/python@sha256:8cbe7fcd5df843c789eb26a3d3059859469441633d6e671111f31553e8dc7156
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/backend \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

RUN apt-get update \
 && apt-get install --no-install-recommends -y libpq5 curl \
 && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --require-hashes --no-deps -r /app/backend/requirements.txt

RUN useradd --create-home --uid 10001 school

COPY --chown=school:school backend /app/backend
COPY --chown=school:school contracts /app/contracts
COPY --chown=school:school pyproject.toml /app/
COPY --chown=school:school infra/prod/entrypoint-api.sh /app/entrypoint-api.sh
COPY --chown=school:school infra/prod/entrypoint-worker.sh /app/entrypoint-worker.sh

RUN chmod +x /app/entrypoint-api.sh /app/entrypoint-worker.sh

USER school
EXPOSE 8000
CMD ["/app/entrypoint-api.sh"]
