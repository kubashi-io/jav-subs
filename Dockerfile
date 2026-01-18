FROM python:3.11-slim

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIDEO_DIR=/videos

WORKDIR /app

# Install system dependencies for lxml (only what's actually needed)
RUN apt-get update && apt-get install -y \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose your app port
EXPOSE 16969

# Run the app with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:16969", "app:app"]
