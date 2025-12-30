# Python 3.11 Base Image
FROM python:3.11-bookworm

# 1. Install System Dependencies (FFmpeg + Browsers Support)
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
    librandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Install Python Libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Install Playwright Browsers (The AI Eyes)
RUN playwright install chromium
RUN playwright install-deps

# 4. Copy Code
COPY . .

# 5. Permissions
RUN mkdir -p captures && chmod 777 captures

# 6. RUN COMMAND (Railway Port Fix)
# Ye command Railway k $PORT variable ko use karegi, agar wo na mila to 8080 use karegi.
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"