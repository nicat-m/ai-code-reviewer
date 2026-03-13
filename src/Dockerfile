FROM python:3.11-slim

# System optimization
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Minimal required packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first
COPY prompt.txt .
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Application selection (gitlab_openai or gitlab_ollama)
ARG APP_MODULE=gitlab_openai
ENV APP_MODULE=${APP_MODULE}

# Copy app code
COPY ${APP_MODULE}.py .

EXPOSE 5000

# Non-root user (security)
RUN useradd -m appuser
USER appuser

CMD uvicorn ${APP_MODULE}:app --host 0.0.0.0 --port 5000
