#!/usr/bin/env python3
"""Startup script for Railway deployment that properly handles PORT environment variable."""
import os
import sys

# Get PORT from environment, default to 5000
port = os.environ.get('PORT', '5000')

# Validate port is a number
try:
    port_int = int(port)
    if port_int < 1 or port_int > 65535:
        print(f"Error: Invalid port number: {port_int}", file=sys.stderr)
        sys.exit(1)
except ValueError:
    print(f"Error: PORT must be a number, got: {port}", file=sys.stderr)
    sys.exit(1)

# Start gunicorn
os.execvp('gunicorn', [
    'gunicorn',
    '-w', '4',
    '-b', f'0.0.0.0:{port}',
    'app:app'
])

