# TaskBoard frontend - multi-stage: Node builds, Nginx serves. Non-root.
# Name: Hemang | Enrollment number: 24bcs10209

# ---------- stage 1: build with Node ----------
FROM node:22-alpine AS build
WORKDIR /app

COPY package.json ./
RUN npm install

COPY vite.config.js index.html ./
COPY src ./src
RUN npm run build          # -> /app/dist

# ---------- stage 2: serve with Nginx ----------
FROM nginx:1.27-alpine

# Unprivileged nginx needs three things: a port above 1024, a writable pid
# path (the default /run/nginx.pid is root-owned), and ownership of the dirs
# the entrypoint's envsubst step writes into.
# Patch the base image's OS packages first - the published nginx:alpine tag
# lags behind Alpine's security updates (OpenSSL / c-ares CVEs).
RUN apk upgrade --no-cache

RUN addgroup -g 10002 -S web && adduser -u 10002 -S web -G web \
 && sed -i 's|^pid .*|pid /tmp/nginx.pid;|' /etc/nginx/nginx.conf \
 && sed -i '/^user /d' /etc/nginx/nginx.conf \
 && mkdir -p /var/cache/nginx \
 && chown -R web:web /var/cache/nginx /usr/share/nginx/html /etc/nginx/conf.d

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template

ENV BACKEND_HOST=backend \
    BACKEND_PORT=8000

USER 10002
EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
