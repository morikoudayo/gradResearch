FROM ubuntu:22.04

ENV DISPLAY=:99
ENV XDG_RUNTIME_DIR=/tmp/runtime

RUN apt-get update && apt-get install -y \
    xvfb \
    x11-utils \
    pipewire \
    pipewire-pulse \
    pulseaudio-utils \
    ffmpeg \
    python3 \
    python3-pip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip3 install playwright && \
    playwright install chromium && \
    playwright install-deps chromium

COPY capture.py /app/
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
