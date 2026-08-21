FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN addgroup --system foodlab \
    && adduser --system --ingroup foodlab --home /app foodlab \
    && mkdir -p /app/instance /app/frontend/images/uploads /app/backups \
    && chown -R foodlab:foodlab /app/instance /app/frontend/images/uploads /app/backups
USER foodlab
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--worker-tmp-dir", "/tmp", "--no-control-socket", "--access-logfile", "-", "--error-logfile", "-", "--timeout", "60", "backend.wsgi:app"]
