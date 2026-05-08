#!/usr/bin/env python3

import sys
import subprocess
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

def capture_youtube(url, output_dir="/output", duration=60):
    """YouTube動画を再生してキャプチャ"""
    print(f"Capturing {url} for {duration}s to {output_dir}")

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    image_pattern = os.path.join(output_dir, "frame_%04d.jpg")
    audio_file = os.path.join(output_dir, "audio.mp3")

    video_process = None
    audio_process = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--autoplay-policy=no-user-gesture-required',
                    '--enable-audio-service-sandbox=false',
                    '--disable-features=AudioServiceOutOfProcess',
                ]
            )

            page = browser.new_page(viewport={'width': 1920, 'height': 1080})
            page.goto(url, wait_until='domcontentloaded')

            video_cmd = [
                'ffmpeg',
                '-f', 'x11grab',
                '-video_size', '1920x1080',
                '-i', ':99',
                '-vf', 'fps=2',
                '-q:v', '2',
                '-t', str(duration),
                '-y',
                image_pattern
            ]

            audio_cmd = [
                'ffmpeg',
                '-f', 'pulse',
                '-i', 'virtual_speaker.monitor',
                '-c:a', 'libmp3lame',
                '-b:a', '192k',
                '-t', str(duration),
                '-y',
                audio_file
            ]

            print(f"Recording for {duration}s...")
            video_process = subprocess.Popen(
                video_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            audio_process = subprocess.Popen(
                audio_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            video_exit = video_process.wait(timeout=duration + 10)
            audio_exit = audio_process.wait(timeout=duration + 10)

            if video_exit != 0:
                print(f"Video capture failed: exit {video_exit}")
            if audio_exit != 0:
                print(f"Audio capture failed: exit {audio_exit}")

            browser.close()
            print("Capture complete")

    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        for proc in [video_process, audio_process]:
            if proc and proc.poll() is None:
                proc.terminate()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: capture.py <youtube_url> [output_dir] [duration]")
        sys.exit(1)

    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "/output"
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 60

    capture_youtube(url, output_dir, duration)
