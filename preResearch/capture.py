#!/usr/bin/env python3

import sys
import subprocess
import os
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

def capture_youtube(url, output_dir="/output"):
    """YouTube動画を再生して広告をキャプチャし、動画を最後まで見て関連動画に移動"""
    import random

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

            print(f"Starting continuous ad capture from {url}")

            # 無限ループで広告を監視し続ける
            while True:
                video_process = None
                audio_process = None

                try:
                    # ページを読み込む（初回または関連動画から）
                    print("\nLoading page...")
                    page.goto(url, wait_until='domcontentloaded')

                    # 広告が表示されるか確認（タイムアウト10秒）
                    print("Checking for ad...")
                    ad_found = False
                    try:
                        page.wait_for_selector('.ad-showing', timeout=10000)
                        print("Ad detected!")
                        ad_found = True
                    except Exception:
                        print("No ad found")

                    # 広告が見つかった場合のみキャプチャ
                    if ad_found:
                        # 日時フォルダを作成
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_base = os.path.join(output_dir, timestamp)
                        output_path = output_base

                        # 重複する場合はサフィックスを追加
                        suffix = 1
                        while os.path.exists(output_path):
                            output_path = f"{output_base}-{suffix}"
                            suffix += 1

                        os.makedirs(output_path, exist_ok=True)
                        print(f"Saving to {output_path}")

                        image_pattern = os.path.join(output_path, "frame_%04d.jpg")
                        audio_file = os.path.join(output_path, "audio.mp3")

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

                        print("Capture complete")

                    # 動画が終わるまで待つ
                    print("Watching video until end...")
                    page.wait_for_function("() => document.querySelector('video').ended")
                    print("Video ended")

                    # 右サイドバーから関連動画を取得してランダムに選ぶ
                    print("Looking for related videos...")
                    related_videos = page.query_selector_all('yt-lockup-view-model a[href^="/watch"]')
                    if related_videos:
                        selected = random.choice(related_videos)
                        next_url = "https://www.youtube.com" + selected.get_attribute('href')
                        print(f"Selected next video: {next_url}")
                        url = next_url
                    else:
                        print("No related videos found, reloading same video")

                except (KeyboardInterrupt, SystemExit):
                    # シグナル受信時はループを抜ける
                    break
                except Exception as e:
                    print(f"Error in capture loop: {e}")
                    # エラーが起きても継続
                    continue
                finally:
                    # プロセスのクリーンアップ
                    for proc in [video_process, audio_process]:
                        if proc and proc.poll() is None:
                            proc.terminate()

            browser.close()
            print("Capture stopped")

    except Exception as e:
        print(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: capture.py <youtube_url> [output_dir]")
        sys.exit(1)

    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "/output"

    try:
        capture_youtube(url, output_dir)
    except KeyboardInterrupt:
        print("\nStopped by user")
        sys.exit(0)
