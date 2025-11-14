# use a small, official Python base
FROM python:3.11-slim

# ---- build-time metadata ----
LABEL maintainer="jhaptech@gmail.com"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ---- install system deps required for some Python packages ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    gcc \
    libffi-dev \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---- app user for non-root runtime ----
RUN useradd --create-home appuser
WORKDIR /home/appuser/app

# copy only requirements first (leverages cache)
COPY --chown=appuser:appuser requirements.txt ./

# upgrade pip and install Python deps
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# ensure upload/log directories exist
RUN mkdir -p static/files logs

ENV PATH="/home/appuser/.local/bin:${PATH}"

# copy app source
COPY --chown=appuser:appuser . .

# expose the port gunicorn will bind to
EXPOSE 8000

# set Flask config defaults (can be overridden by env)
ENV FLASK_APP=app.py \
    FLASK_ENV=production \
    PORT=8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=5 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

USER appuser

# use Gunicorn to serve the app in production
# - use a threaded worker class
CMD ["gunicorn", "--workers", "4", "--threads", "2", "--bind", "0.0.0.0:8000", "app:app"]
