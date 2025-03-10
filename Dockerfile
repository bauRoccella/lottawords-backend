FROM selenium/standalone-chrome:latest

# Install Python 3.11 and pip
USER root
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
    python3.11-full \
    python3.11-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Create and activate virtual environment
ENV VIRTUAL_ENV=/app/venv
RUN python3.11 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy the entire application first
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Install dependencies and the local package
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install -e .

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV SELENIUM_DRIVER_HOST=/usr/bin/chromedriver
ENV DISPLAY=:99
ENV TZ=UTC

# Create necessary directories and set permissions
RUN mkdir -p /app/logs && \
    chmod -R 755 /app

# Expose port (this is just documentation, the actual port will be from PORT env var)
EXPOSE 8000

# Run the application using the start script
CMD ["./start.sh"] 