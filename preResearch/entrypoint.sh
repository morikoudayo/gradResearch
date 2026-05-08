#!/bin/bash

set -e

# ランタイムディレクトリを作成
mkdir -p $XDG_RUNTIME_DIR

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

echo "Starting PulseAudio..."
pulseaudio --start --log-target=stderr &
PULSEAUDIO_PID=$!

# PulseAudioの起動を確認
echo "Waiting for PulseAudio..."
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
echo "PulseAudio ready"

echo "Starting capture script..."
if [ -n "$YOUTUBE_URL" ]; then
    python3 /app/capture.py "$YOUTUBE_URL" /output "${DURATION:-60}"
else
    python3 /app/capture.py "$@"
fi

pulseaudio --kill 2>/dev/null || true
kill $XVFB_PID 2>/dev/null || true
