FROM python:3.11-slim-bookworm

# Install system dependencies: FFmpeg, build essentials, fonts
RUN apt-get update -y && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    gcc \
    python3-dev \
    libffi-dev \
    fontconfig \
    fonts-dejavu-core \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Run entrypoint
CMD ["python3", "-m", "wirq"]
