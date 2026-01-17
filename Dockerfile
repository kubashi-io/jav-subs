FROM python:3.12-slim

# Install system deps (lxml needs these)
RUN apt-get update && apt-get install -y \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY downloader.py app.py ./

# Default video root inside container
ENV VIDEO_ROOT_DIR=/videos

EXPOSE 8000

CMD ["python", "app.py"]
