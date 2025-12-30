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

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p output uploads

# Expose port 5000
EXPOSE 5000

# Start gunicorn on port 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]

