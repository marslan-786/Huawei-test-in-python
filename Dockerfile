FROM python:3.11-bookworm

# Install System Dependencies
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
    fonts-liberation \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Requirements
COPY requirements.txt .

# Install Python Libs (Ensure Upgrade)
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright
RUN playwright install chromium
RUN playwright install-deps

# Copy Source
COPY . .
RUN mkdir -p captures && chmod 777 captures

# Run
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"