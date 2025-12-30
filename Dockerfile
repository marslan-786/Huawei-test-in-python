FROM python:3.11-bookworm

# 1. Install Desktop Environment & Chrome
RUN apt-get update && apt-get install -y \
    chromium \
    xvfb \
    x11vnc \
    fluxbox \
    novnc \
    net-tools \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# 2. Environment Variables
ENV DISPLAY=:0
ENV RESOLUTION=1280x720

# 3. Setup Workspace
WORKDIR /app

# 4. Copy Start Scripts
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY start.sh .

# 5. Permissions
RUN chmod +x start.sh

# 6. Start Command (Supervisor runs everything)
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]