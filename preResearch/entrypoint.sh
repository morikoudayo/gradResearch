#!/bin/bash

set -e

wait_for_service() {
    local check_cmd="$1"
    local service_name="$2"
    local max_retries=10

    echo "Waiting for $service_name..."
    local retry=0
    until eval "$check_cmd" >/dev/null 2>&1 || [ $retry -eq $max_retries ]; do
        retry=$((retry + 1))
        sleep 0.5
    done
    echo "$service_name ready"
}

mkdir -p $XDG_RUNTIME_DIR

echo "Starting Xvfb..."
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!
wait_for_service "xdpyinfo -display :99" "Xvfb"

echo "Starting PulseAudio..."
pulseaudio --start --log-target=stderr
wait_for_service "pactl info" "PulseAudio"

echo "Creating virtual audio sink..."
pactl load-module module-null-sink sink_name=virtual_speaker sink_properties=device.description="Virtual_Speaker" >/dev/null
pactl set-default-sink virtual_speaker

echo "Audio setup complete"
pactl list short sinks
pactl list short sources

echo "Starting capture script..."
if [ -n "$YOUTUBE_URL" ]; then
    python3 /app/capture.py "$YOUTUBE_URL" /output "${DURATION:-60}"
else
    python3 /app/capture.py "$@"
fi

pulseaudio --kill 2>/dev/null || true
kill $XVFB_PID 2>/dev/null || true
