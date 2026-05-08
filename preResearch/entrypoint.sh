#!/bin/bash

set -e

# ランタイムディレクトリを作成
mkdir -p $XDG_RUNTIME_DIR

# dbus を起動
echo "Starting dbus..."
mkdir -p /var/run/dbus
dbus-daemon --system --fork

# dbus の起動を確認
echo "Waiting for dbus..."
RETRY=0
until test -S /var/run/dbus/system_bus_socket || [ $RETRY -eq 10 ]; do
    RETRY=$((RETRY + 1))
    sleep 0.5
done
echo "dbus ready"

echo "Starting Xvfb..."
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!

# Xvfbの起動を確認
echo "Waiting for Xvfb..."
RETRY=0
until xdpyinfo -display :99 >/dev/null 2>&1 || [ $RETRY -eq 10 ]; do
    RETRY=$((RETRY + 1))
    sleep 0.5
done
echo "Xvfb ready"

echo "Starting Pipewire..."
pipewire &
PIPEWIRE_PID=$!
sleep 1

echo "Starting Pipewire Pulse..."
pipewire-pulse &
PIPEWIRE_PULSE_PID=$!

# Pipewire Pulseの起動を確認
echo "Waiting for Pipewire Pulse..."
RETRY=0
until pactl info >/dev/null 2>&1 || [ $RETRY -eq 10 ]; do
    RETRY=$((RETRY + 1))
    sleep 0.5
done

# 仮想オーディオシンクを作成
echo "Creating virtual audio sink..."
pactl load-module module-null-sink sink_name=virtual_speaker sink_properties=device.description="Virtual_Speaker"

# デフォルトシンクを設定
pactl set-default-sink virtual_speaker

# オーディオデバイスの確認
echo "Checking audio devices..."
pactl list short sinks
pactl list short sources
echo "Default sink:"
pactl get-default-sink
echo "Pipewire ready"

echo "Starting capture script..."
if [ -n "$YOUTUBE_URL" ]; then
    python3 /app/capture.py "$YOUTUBE_URL" /output "${DURATION:-60}"
else
    python3 /app/capture.py "$@"
fi

kill $XVFB_PID $PIPEWIRE_PID $PIPEWIRE_PULSE_PID 2>/dev/null || true
