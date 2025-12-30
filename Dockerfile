# Use Python 3.13 official image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies (ffmpeg for audio processing, espeak-ng for TTS)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    espeak-ng \
    espeak-ng-data \
    libespeak-ng1 \
    && rm -rf /var/lib/apt/lists/* && \
    # Create symlink for espeak compatibility (pyttsx3 looks for 'espeak')
    ln -sf /usr/bin/espeak-ng /usr/bin/espeak

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_ENV=production
ENV PORT=5000

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p output uploads

# Expose port (Railway will set PORT env var)
EXPOSE 5000

# Use bash to execute command so $PORT variable is properly expanded
# Railway/Koyeb require shell expansion for environment variables in CMD
CMD ["/bin/bash", "-c", "gunicorn -w 4 -b 0.0.0.0:${PORT:-5000} app:app"]

