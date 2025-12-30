#!/bin/sh
# Startup script for Railway deployment
# Handles PORT environment variable properly

# Get PORT from environment, default to 5000 if not set
PORT="${PORT:-5000}"

# Validate PORT is a number
if ! echo "$PORT" | grep -qE '^[0-9]+$'; then
    echo "Error: PORT must be a number, got: $PORT" >&2
    exit 1
fi

# Check if PORT is in valid range
if [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    echo "Error: PORT must be between 1 and 65535, got: $PORT" >&2
    exit 1
fi

# Start gunicorn
# exec gunicorn -w 4 -b "0.0.0.0:${PORT}" app:app
exec gunicorn -w 4 -b "0.0.0.0:5000" app:app
