#!/usr/bin/env python3

import sys
import time
import subprocess
import os
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

def get_pulse_source():
    """
    利用可能な PulseAudio ソースを取得する
    仮想シンクのモニターを優先的に使用
    """
    try:
        result = subprocess.run(
            ['pactl', 'list', 'short', 'sources'],
            capture_output=True,
            text=True,
            check=True
        )
        sources = result.stdout.strip().split('\n')

        # 仮想シンクのモニターを探す
        for source in sources:
            if 'virtual_speaker.monitor' in source:
                source_name = source.split()[1]
                print(f"Found virtual speaker monitor: {source_name}")
                return source_name

        # 見つからなければ最初のソース
        if sources and sources[0]:
            source_name = sources[0].split()[1]
            print(f"Found audio source: {source_name}")
            return source_name
        else:
            print("No audio sources found, using 'default'")
            return 'default'
    except Exception as e:
        print(f"Error detecting audio source: {e}")
        return 'default'

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

    # 利用可能なオーディオソースを検出
    audio_source = get_pulse_source()

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

            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True
            )

            page = context.new_page()

            page.goto(url, wait_until='domcontentloaded')

            # YouTube の動画が読み込まれるまで待つ
            time.sleep(3)

            # 動画を再生（必要に応じて）
            try:
                play_button = page.locator('button.ytp-large-play-button')
                if play_button.is_visible(timeout=2000):
                    play_button.click()
                    print("Clicked play button")
            except Exception as e:
                print(f"Play button not found or already playing: {e}")

            # 少し待ってから録音開始
            time.sleep(2)

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

            print(f"Starting audio recording from source: {audio_source}...")
            audio_cmd = [
                'ffmpeg',
                '-f', 'pulse',
                '-i', audio_source,
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
            video_exit_code = video_process.wait(timeout=10)
            audio_exit_code = audio_process.wait(timeout=10)

            print(f"Screen capture exit code: {video_exit_code}")
            print(f"Audio recording exit code: {audio_exit_code}")

            # エラー出力を表示
            if video_exit_code != 0:
                _, stderr = video_process.communicate()
                print(f"Screen capture error: {stderr.decode()}")

            if audio_exit_code != 0:
                _, stderr = audio_process.communicate()
                print(f"Audio recording error: {stderr.decode()}")

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
