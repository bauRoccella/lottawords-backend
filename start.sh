#!/bin/bash

# Exit on error
set -e

# Default to port 8000 if PORT is not set
PORT="${PORT:-8000}"

# Wait for system to be ready
sleep 2

# Ensure timezone data is available
if [ ! -f "/usr/share/zoneinfo/UTC" ]; then
    echo "Installing tzdata..."
    apt-get update && apt-get install -y tzdata
fi

# Ensure virtual environment exists
if [ ! -d "/app/venv" ]; then
    echo "Creating virtual environment..."
    python -m venv /app/venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
. /app/venv/bin/activate

# Verify virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "ERROR: Failed to activate virtual environment"
    exit 1
fi

echo "Starting gunicorn..."
# Start gunicorn with error logging
exec gunicorn app:app \
    --bind "0.0.0.0:$PORT" \
    --workers 2 \
    --timeout 120 \
    --log-level info \
    --error-logfile /app/logs/gunicorn-error.log \
    --access-logfile /app/logs/gunicorn-access.log \
    --capture-output 