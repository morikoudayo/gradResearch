#!/usr/bin/env python3

import sys
import time
import subprocess
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

def capture_youtube(url, output_dir="/output", duration=60):
    """
    指定されたYouTube URLの動画を再生してキャプチャする

    Args:
        url: YouTube動画のURL
        output_dir: 出力ディレクトリ
        duration: キャプチャ時間（秒）
    """
    print(f"Capturing YouTube video: {url}")
    print(f"Output directory: {output_dir}")
    print(f"Duration: {duration} seconds")

    # 出力ディレクトリを作成
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 出力ファイルパス
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
                ]
            )

            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True
            )

            page = context.new_page()

            page.goto(url, wait_until='domcontentloaded')

            print("Starting screen capture (2 FPS JPEG)...")
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

            print("Starting audio recording...")
            audio_cmd = [
                'ffmpeg',
                '-f', 'pulse',
                '-i', 'default',
                '-c:a', 'libmp3lame',
                '-b:a', '192k',
                '-t', str(duration),
                '-y',
                audio_file
            ]

            # 画面キャプチャと音声録音を並列実行
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

            print(f"Recording for {duration} seconds...")
            time.sleep(duration + 2)

            print("Waiting for processes to finish...")
            video_process.wait(timeout=10)
            audio_process.wait(timeout=10)

            browser.close()

            print(f"Screen capture completed: {image_pattern}")
            print(f"Audio recording completed: {audio_file}")

    except Exception as e:
        print(f"Error during capture: {e}")
        if video_process:
            video_process.terminate()
        if audio_process:
            audio_process.terminate()
        raise
    finally:
        if video_process and video_process.poll() is None:
            video_process.terminate()
        if audio_process and audio_process.poll() is None:
            audio_process.terminate()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 capture.py <youtube_url> [output_dir] [duration]")
        print("Example: python3 capture.py https://www.youtube.com/watch?v=dQw4w9WgXcQ /output 30")
        sys.exit(1)

    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "/output"
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 60

    capture_youtube(url, output_dir, duration)
