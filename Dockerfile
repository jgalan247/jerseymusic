# Multi-stage Dockerfile for Jersey Music Django application on Railway
# Uses Python 3.11 with Node.js for Tailwind CSS compilation

FROM python:3.11-slim

# Force unbuffered Python output so logs appear immediately in Railway
ENV PYTHONUNBUFFERED=1

# Install Node.js 18 and npm for frontend tooling
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY requirements.txt package.json package-lock.json ./

# Install Python dependencies using python3 -m pip (more reliable than pip command)
RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    python3 -m pip install --no-cache-dir -r requirements.txt

# Install Node.js dependencies
RUN npm ci

# Copy the rest of the application
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Create logs directory for Django-Q and payment polling
RUN mkdir -p logs

# Collect static files during build to speed up container startup
# DOCKER_BUILD=true bypasses production validation during build
# LOCAL_TEST=True and DEBUG=True configure SQLite (collectstatic doesn't need actual DB)
# This prevents Railway health check timeouts by reducing startup time
ENV DOCKER_BUILD=true
ENV LOCAL_TEST=True
ENV DEBUG=True
ENV SECRET_KEY=build-time-secret-key-for-collectstatic-only
RUN python manage.py collectstatic --noinput --clear && \
    echo "✅ Static files collected during Docker build"

# Expose port (Railway will set the PORT env var)
EXPOSE ${PORT:-8000}

# Start command - runs migrations and starts gunicorn
CMD ["bash", "start.sh"]
