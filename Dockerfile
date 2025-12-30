FROM python:3.11-bookworm

# 1. Install System Tools
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    chromium \
    xvfb \
    x11vnc \
    fluxbox \
    novnc \
    websockify \
    supervisor \
    net-tools \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 2. Setup Display Env
ENV DISPLAY=:0
ENV RESOLUTION=1280x720

WORKDIR /app

# 3. Copy Config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 4. Start
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]