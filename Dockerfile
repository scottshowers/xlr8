FROM python:3.11-slim

# Install system dependencies including tesseract and poppler
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Start command - Railway sets PORT env var
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
