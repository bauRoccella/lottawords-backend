FROM python:3.9-slim

# Install Chrome and ChromeDriver
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    chromium \
    chromium-driver \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Create virtual environment
RUN python -m venv venv
ENV PATH="/app/venv/bin:$PATH"

# Copy requirements first
COPY requirements.txt .
COPY setup.py .
COPY MANIFEST.in .
COPY src ./src

# Install dependencies in virtual environment
RUN . /app/venv/bin/activate && \
    pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --verbose --no-cache-dir -r requirements.txt && \
    pip install --verbose -e .

# Copy the rest of the application
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV SELENIUM_DRIVER_HOST=/usr/bin/chromedriver
ENV DISPLAY=:99
ENV TZ=UTC
# Configure Chrome to run in no-sandbox mode
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROME_PATH=/usr/bin/chromium
ENV CHROME_OPTIONS="--no-sandbox --headless --disable-gpu --disable-dev-shm-usage"
ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Create necessary directories and set permissions
RUN mkdir -p /app/logs && \
    chmod -R 755 /app

# Expose port
EXPOSE 8000

# Run the application
CMD ["./start.sh"] 