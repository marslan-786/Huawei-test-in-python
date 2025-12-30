# Base Image Python 3.11
FROM python:3.11-bookworm

# 1. System Dependencies (FFmpeg + Browsers Support)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Python Libraries Install
COPY requirements.txt .
RUN pip install --no-cache-dir -U -r requirements.txt

# 3. Install Playwright Browsers (The AI Eyes)
RUN playwright install chromium
RUN playwright install-deps

# 4. Copy Code
COPY . .

# 5. Create Captures Folder & Permissions
RUN mkdir -p captures && chmod 777 captures

# 6. RUN COMMAND (Railway Port Variable Fix)
# Ye line Railway k $PORT ko automatic utha legi.
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"