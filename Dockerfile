FROM python:3.11-bookworm

# Install Dependencies
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

# Install Python Libs (No Cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -U -r requirements.txt

# Install Playwright
RUN playwright install chromium
RUN playwright install-deps

# Copy Code
COPY . .
RUN mkdir -p captures && chmod 777 captures

# Run
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"