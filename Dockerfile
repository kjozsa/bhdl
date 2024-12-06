FROM python:3.11-slim-bullseye as builder

# Install build dependencies and create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim-bullseye

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Chrome dependencies with minimal layers
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    google-chrome-stable \
    && apt-get purge -y wget gnupg \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/* \
    && rm -rf /root/.cache/*

# Chrome optimization flags
ENV CHROME_FLAGS="--headless --no-sandbox --disable-dev-shm-usage --disable-gpu --disable-software-rasterizer --disable-extensions --single-process"
ENV DISPLAY=:99

# Create app directory and user
RUN useradd -m -r chrome \
    && mkdir -p /app /downloads \
    && chown -R chrome:chrome /app /downloads

WORKDIR /app
USER chrome

# Copy application files
COPY --chown=chrome:chrome . .

# Create downloads directory
VOLUME /downloads

# Set environment variables
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=5000
ENV HEADLESS=true
ENV DOWNLOAD_DIR=/downloads

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
