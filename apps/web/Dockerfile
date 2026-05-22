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
RUN pnpm --filter web build

FROM node:22-slim AS runtime
WORKDIR /app
RUN npm install -g serve@14
COPY --from=build /app/apps/web/dist ./dist
# Railway injects PORT; serve binds 0.0.0.0 by default. -s = SPA fallback.
CMD ["sh", "-c", "serve -s dist -l ${PORT:-8080}"]
