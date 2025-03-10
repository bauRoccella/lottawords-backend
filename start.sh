#!/bin/bash

# Exit on error
set -e

# Enable command logging
set -x

# Default to port 8000 if PORT is not set
PORT="${PORT:-8000}"

# Print environment information
echo "Current directory: $(pwd)"
echo "Python version: $(python3 --version)"
echo "Directory contents: $(ls -la)"

# Install dependencies directly (no virtualenv in production)
pip install -r requirements.txt

# Print installed packages
echo "Installed Python packages:"
pip list

echo "Starting gunicorn..."
# Start gunicorn with minimal configuration
exec gunicorn app:app \
    --bind "0.0.0.0:$PORT" \
    --workers 1 \
    --timeout 30 \
    --log-level debug \
    --error-logfile - \
    --access-logfile - \
    --capture-output 