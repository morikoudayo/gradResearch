#!/usr/bin/env python3

import sys
import subprocess
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

def capture_youtube(url, output_dir="/output"):
    """YouTube動画を再生して広告が表示されている間だけキャプチャ"""
    print(f"Capturing ads from {url} to {output_dir}")

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

            # 広告が表示されるまで待つ（タイムアウト10秒）
            print("Waiting for ad to appear...")
            try:
                page.wait_for_selector('.ad-showing', timeout=10000)
                print("Ad detected, starting capture...")
            except Exception:
                print("No ad found within 10 seconds, exiting")
                browser.close()
                return

            video_cmd = [
                'ffmpeg',
                '-f', 'x11grab',
                '-video_size', '1920x1080',
                '-i', ':99',
                '-vf', 'fps=2',
                '-q:v', '2',
                '-y',
                image_pattern
            ]

            audio_cmd = [
                'ffmpeg',
                '-f', 'pulse',
                '-i', 'virtual_speaker.monitor',
                '-c:a', 'libmp3lame',
                '-b:a', '192k',
                '-y',
                audio_file
            ]

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

            # 広告が消えるまで待つ
            print("Recording ad...")
            page.wait_for_selector('.ad-showing', state='detached')
            print("Ad finished, stopping capture...")

            # 録画を停止
            video_process.terminate()
            audio_process.terminate()

            video_exit = video_process.wait(timeout=10)
            audio_exit = audio_process.wait(timeout=10)

            if video_exit not in (0, -15):
                print(f"Video capture failed: exit {video_exit}")
            if audio_exit not in (0, -15):
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
        print("Usage: capture.py <youtube_url> [output_dir]")
        sys.exit(1)

    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "/output"

    capture_youtube(url, output_dir)
