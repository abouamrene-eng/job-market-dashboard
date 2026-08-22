# Docker deploy (instead of Render's native Python runtime) so weasyprint's
# native libraries (Pango/Cairo/GDK-Pixbuf) are actually present at runtime.
# Without them, cv_generator.py silently falls back to the older reportlab
# CV - it still works, just not the premium indigo/Lato/Space Grotesk one.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libcairo2 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render injects $PORT at runtime; the default here only matters for local
# `docker run`.
ENV PORT=10000
EXPOSE 10000

CMD gunicorn app:app --workers 1 --timeout 120 --bind 0.0.0.0:$PORT
