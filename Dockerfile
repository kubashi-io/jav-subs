FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY downloader.py .
COPY templates ./templates
COPY static ./static

# Environment variables
ENV VIDEO_ROOT_DIR=/videos

# Expose Flask port
EXPOSE 16969

# Run the app
CMD ["python", "app.py"]
