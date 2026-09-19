# Frontend image for development and CI.
#
# Installs from the committed package-lock.json with `npm ci`, so the tree is
# reproducible. Base image pinned by digest via the ARG Compose supplies.
ARG NODE_IMAGE=docker.io/library/node@sha256:b6f26b36c8ff49624cfdac716b8ea1138d606df02586a77d364bb5536a634f85
FROM ${NODE_IMAGE}

ENV CI=true
WORKDIR /app/frontend

# Everything is owned by the unprivileged `node` user from the start. Vite writes a
# temporary bundle of its config NEXT TO vite.config.ts when loading it
# (vite.config.ts.timestamp-*.mjs), so a root-owned working directory makes the dev
# server die with EACCES the moment it starts -- which is exactly what the first
# real container run did. Running as root would "fix" it and create root-owned files
# in the developer's checkout through the bind mount, so ownership is the fix.
RUN mkdir -p /app/frontend /app/contracts && chown -R node:node /app

USER node

# Lockfile first: a source change must not reinstall node_modules.
COPY --chown=node:node frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY --chown=node:node frontend ./
# The generated client is produced from the approved OpenAPI, which lives outside
# frontend/, so it is copied in separately.
COPY --chown=node:node contracts /app/contracts

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
