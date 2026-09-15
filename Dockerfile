FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    unzip \
    aria2 \
    build-essential \
    libopus0 \
    libopus-dev \
    && rm -rf /var/lib/apt/lists/*

# yt-dlp requires a supported JavaScript runtime for current YouTube
# challenge solving. Deno is the recommended runtime.
RUN curl -fsSL https://deno.land/install.sh | sh && \
    ln -sf /root/.deno/bin/deno /usr/local/bin/deno && \
    deno --version

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    python -m yt_dlp --version && \
    python -c "import yt_dlp_ejs; print(\"yt-dlp-ejs OK\")"

COPY . .

RUN mkdir -p downloads cache anony/helpers/assets

CMD ["bash", "start"]
