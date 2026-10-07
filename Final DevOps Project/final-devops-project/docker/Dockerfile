# TaskBoard - multi-stage build.
# Name: Hemang | Enrollment number: 24bcs10209

# ---------- stage 1: build the dependency wheels ----------
FROM python:3.12-slim AS build
WORKDIR /wheels
COPY application/requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ---------- stage 2: runtime ----------
FROM python:3.12-slim
WORKDIR /srv

# a non-root user, because the k8s securityContext requires runAsNonRoot
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin taskboard

COPY --from=build /wheels /wheels
COPY application/requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels

COPY application/app ./app

ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION \
    PYTHONUNBUFFERED=1

USER 10001
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["python", "-m", "app.main"]
