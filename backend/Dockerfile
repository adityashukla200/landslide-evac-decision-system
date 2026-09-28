FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PostgreSQL, GEOS, and compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgeos-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy source trees
COPY backend /app/backend
COPY scripts /app/scripts
 COPY data /app/data
COPY alembic.ini /app/alembic.ini

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
