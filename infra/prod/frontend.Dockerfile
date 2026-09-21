# Production frontend: static Vite build served by nginx (see compose).
# Both base images are declared before the first FROM: an ARG declared between
# stages is not visible to a later FROM line and resolves to blank.
ARG NGINX_IMAGE=docker.io/library/nginx@sha256:a8b39bd9cf0f83869a2162827a0caf6137ddf759d50a171451b335cecc87d236
ARG NODE_IMAGE=docker.io/library/node@sha256:b6f26b36c8ff49624cfdac716b8ea1138d606df02586a77d364bb5536a634f85
FROM ${NODE_IMAGE} AS build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend ./
COPY contracts /app/contracts
# Same-origin API behind nginx — empty base URL.
ENV VITE_SCHOOL_API_URL=
ENV VITE_SCHOOL_MODULE_ID=
RUN npm run build

FROM ${NGINX_IMAGE}
COPY --from=build /app/frontend/dist /usr/share/nginx/html
COPY infra/prod/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
