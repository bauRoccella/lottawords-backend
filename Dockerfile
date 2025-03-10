FROM selenium/standalone-chrome:latest

# Install Python 3.11 and pip
USER root

# Add Debian backports repository
RUN echo "deb http://deb.debian.org/debian bullseye-backports main" > /etc/apt/sources.list.d/backports.list

# Install Python and build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Create and activate virtual environment
ENV VIRTUAL_ENV=/app/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy requirements first
COPY requirements.txt .
COPY setup.py .
COPY MANIFEST.in .
COPY src ./src

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
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

# Create necessary directories and set permissions
RUN mkdir -p /app/logs && \
    chmod -R 755 /app

# Expose port (this is just documentation, the actual port will be from PORT env var)
EXPOSE 8000

# Run the application using the start script
CMD ["./start.sh"] 