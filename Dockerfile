# Multi-stage build for optimization
FROM python:3.11-slim as base

# Build stage for dependencies
FROM base as builder

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
    pip install --user -r /tmp/requirements.txt

# Production stage
FROM base as production

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/root/.local/bin:$PATH

WORKDIR /app

# Install runtime dependencies including OpenGL libraries for video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    libgl1-mesa-dev \
    libglib2.0-0t64 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages from builder stage
COPY --from=builder /root/.local /root/.local

# Create necessary directories and set proper permissions
# Note: instance and logs will be mounted from host via docker-compose
RUN mkdir -p uploads temp_uploads && \
    chmod 755 uploads temp_uploads && \
    chown -R root:root /app

# Copy application files in new structure
COPY src ./src
COPY app.py ./
COPY requirements.txt ./
COPY gcp-credentials.json ./gcp-credentials.json
COPY .env.example ./.env.example

# Copy startup script
COPY startup.sh ./startup.sh
RUN chmod +x startup.sh

# Create default environment file
RUN echo 'FLASK_ENV=production' > .env

# Expose Flask port
EXPOSE 5000

# Use startup script for better initialization
CMD ["./startup.sh"]
