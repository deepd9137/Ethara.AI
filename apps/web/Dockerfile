# Web service — build the Vite bundle, serve it as static files.
# Build context is the repo root (the web service's root directory is "/")
# because pnpm needs the workspace lockfile.
#
# pnpm is installed directly with npm rather than via corepack: the corepack
# shim bundled with current Node releases crashes on pnpm 11.x with
# ERR_VM_DYNAMIC_IMPORT_CALLBACK_MISSING.

FROM node:22-slim AS build
WORKDIR /app
RUN npm install -g pnpm@11.1.2
COPY . .
RUN pnpm install --frozen-lockfile

# Vite inlines VITE_* at build time. Docker RUN steps don't see Railway's
# service variables unless they're declared as build args — Railway passes
# service variables as --build-arg for Dockerfile builds.
ARG VITE_API_BASE_URL
ARG VITE_ENVIRONMENT
ARG VITE_COMMIT_SHA
ARG VITE_SENTRY_DSN
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_ENVIRONMENT=$VITE_ENVIRONMENT \
    VITE_COMMIT_SHA=$VITE_COMMIT_SHA \
    VITE_SENTRY_DSN=$VITE_SENTRY_DSN
RUN pnpm --filter web build

FROM node:22-slim AS runtime
WORKDIR /app
RUN npm install -g serve@14
COPY --from=build /app/apps/web/dist ./dist
# Railway injects PORT; serve binds 0.0.0.0 by default. -s = SPA fallback.
CMD ["sh", "-c", "serve -s dist -l ${PORT:-8080}"]
