FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/zhtyyx/ioe" \
      org.opencontainers.image.description="IOE single-store inventory, checkout and member management" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code only. Databases, uploads and secrets belong to runtime volumes.
COPY manage.py ./
COPY inventory ./inventory
COPY store ./store
COPY project ./project
COPY docker/entrypoint.sh /usr/local/bin/ioe-entrypoint
RUN chmod 755 /usr/local/bin/ioe-entrypoint \
    && mkdir -p /app/db /app/media /app/staticfiles /app/logs /app/backups /app/temp

EXPOSE 8000
ENTRYPOINT ["ioe-entrypoint"]
CMD ["gunicorn", "inventory.wsgi:application", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]
