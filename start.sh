#!/bin/bash
# Startup script for Railway deployment
# Properly handles PORT environment variable

PORT=${PORT:-5000}
exec gunicorn -w 4 -b 0.0.0.0:$PORT app:app

