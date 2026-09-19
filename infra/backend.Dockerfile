# Backend image for development and CI.
#
# Installs from the committed, hash-pinned lockfiles, so a container build
# resolves exactly the wheels the local venv did. The base image is pinned by
# digest in infra/images.json; the ARG below is supplied by Compose so the pin
# lives in one place.
ARG PYTHON_IMAGE=docker.io/library/python@sha256:8cbe7fcd5df843c789eb26a3d3059859469441633d6e671111f31553e8dc7156
FROM ${PYTHON_IMAGE}

# Fail fast and never write .pyc into the bind mount.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# psycopg[binary] ships wheels, so no build toolchain is needed. Only the
# Postgres client library is added, for pg_isready-style diagnostics.
RUN apt-get update \
 && apt-get install --no-install-recommends -y libpq5 curl \
 && rm -rf /var/lib/apt/lists/*

# Dependencies first, so a source change does not invalidate the install layer.
COPY backend/requirements.txt backend/requirements-dev.txt /app/backend/
RUN python -m pip install --require-hashes --no-deps \
        -r /app/backend/requirements.txt \
 && python -m pip install --require-hashes --no-deps \
        -r /app/backend/requirements-dev.txt

# Unprivileged by default. A development container running as root writes
# root-owned files into the developer's checkout through the bind mount, and Django
# needs a writable home for nothing in particular -- but a writable app directory
# matters for anything that caches beside its source.
RUN useradd --create-home --uid 10001 school

# Source arrives via a bind mount in development; copying it here keeps the image
# usable standalone (CI, and later M14's production build). Owned by the runtime
# user for the same reason the frontend image is.
COPY --chown=school:school backend /app/backend
COPY --chown=school:school contracts /app/contracts
COPY --chown=school:school pyproject.toml /app/

ENV PYTHONPATH=/app/backend

USER school

EXPOSE 8000
CMD ["python", "backend/manage.py", "runserver", "0.0.0.0:8000"]
