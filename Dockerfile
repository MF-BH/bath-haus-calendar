FROM python:3.12-slim

# Install system dependencies for weasyprint (PDF generation)
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libffi-dev \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir \
    flask>=3.0.3 \
    gunicorn>=22.0.0 \
    pyswisseph>=2.10.3 \
    geopy>=2.4.1 \
    timezonefinder>=6.5.2 \
    pytz>=2024.1 \
    weasyprint>=62.3 \
    python-dotenv>=1.0.1 \
    sendgrid>=6.11.0 \
    anthropic>=0.25.0

# Copy all app files
COPY astro_calc.py .
COPY astro_alignments.py .
COPY personalization.py .
COPY calendar_generator.py .
COPY generate_calendar.py .
COPY app.py .

# Output directory for generated calendars
RUN mkdir -p /tmp/calendars
RUN mkdir -p /app/ephe

# Expose port (Railway sets PORT env var automatically)
EXPOSE 5000

# Run with gunicorn in production
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app
