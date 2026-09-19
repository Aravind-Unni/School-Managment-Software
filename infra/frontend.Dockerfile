# Frontend image for development and CI.
#
# Installs from the committed package-lock.json with `npm ci`, so the tree is
# reproducible. Base image pinned by digest via the ARG Compose supplies.
ARG NODE_IMAGE=docker.io/library/node@sha256:b6f26b36c8ff49624cfdac716b8ea1138d606df02586a77d364bb5536a634f85
FROM ${NODE_IMAGE}

ENV CI=true
WORKDIR /app/frontend

# Lockfile first: a source change must not reinstall node_modules.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend ./
# The generated client is produced from the approved OpenAPI, which lives
# outside frontend/, so it is copied in separately.
COPY contracts /app/contracts

# node's own unprivileged user, for the same bind-mount reason as the backend.
USER node

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
