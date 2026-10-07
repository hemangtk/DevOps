# Stacks backend - multi-stage, non-root.
# Name: Hemang | Enrollment number: 24bcs10209

# ---------- stage 1: build wheels ----------
FROM python:3.12-slim AS build
WORKDIR /wheels
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ---------- stage 2: runtime ----------
FROM python:3.12-slim
WORKDIR /srv

RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin appuser

COPY --from=build /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER 10001
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
