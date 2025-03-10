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

# Create logs directory
mkdir -p /app/logs
chmod 777 /app/logs

# Print expected URL
if [ ! -z "$RAILWAY_PUBLIC_DOMAIN" ]; then
    echo "Application should be available at: https://$RAILWAY_PUBLIC_DOMAIN"
fi

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

# Print installed packages
echo "Installed Python packages:"
pip list

# Install dependencies
pip install -r requirements.txt

echo "Starting gunicorn..."
# Start gunicorn with error logging
exec gunicorn app:app \
    --bind "0.0.0.0:$PORT" \
    --workers 1 \
    --timeout 120 \
    --log-level debug \
    --error-logfile - \
    --access-logfile - \
    --capture-output \
    --reload \
    --spew 