# CI/CD demo image
# Name: Hemang | Enrollment number: 24bcs10209
FROM python:3.12-slim

WORKDIR /srv

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION

# Run as a non-root user. The Kubernetes manifests in DevSecOps/k8s/ set
# runAsNonRoot: true, which REFUSES to start an image whose USER resolves
# to uid 0 - so this has to be here, not only in the pod spec.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin appuser \
 && chown -R appuser:appuser /srv
USER 10001

EXPOSE 5000
CMD ["python", "-m", "app.main"]
