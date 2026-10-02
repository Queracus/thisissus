# API and worker image (same code, different command in docker-compose.yml).
FROM python:3.12-slim

# ffmpeg: video conversion + posters (photos/HEIC need nothing extra: Pillow + pillow-heif wheels).
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .
COPY migrations ./migrations

RUN useradd --create-home thisissus && mkdir -p /export && chown thisissus /export
USER thisissus
# config.py resolves migrations as <root>/backend/migrations; point it at this image's layout.
ENV MIGRATIONS_DIR=/app/migrations
