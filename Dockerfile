FROM selenium/standalone-chrome:latest

# Install Python and pip
USER root
RUN apt-get update && apt-get install -y \
    python3-full \
    python3-pip \
    python3-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Create and activate virtual environment
ENV VIRTUAL_ENV=/app/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy the entire application first
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Install dependencies and the local package
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install -e .

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV SELENIUM_DRIVER_HOST=/usr/bin/chromedriver
ENV DISPLAY=:99

# Expose port (this is just documentation, the actual port will be from PORT env var)
EXPOSE 8000

# Run the application using the start script
CMD ["./start.sh"] 