#!/bin/bash

# Default to port 8000 if PORT is not set
PORT="${PORT:-8000}"

# Start gunicorn
exec gunicorn app:app --bind "0.0.0.0:$PORT" --workers 2 --timeout 120 