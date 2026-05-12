#!/usr/bin/env python3

import sys
import subprocess
import os
import random
import json
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

def capture_youtube(url, output_dir="/output", auth_file="/auth/auth.json"):
    """YouTube動画を再生して広告をキャプチャし、動画を最後まで見て関連動画に移動"""
    # 認証情報を読み込む
    auth_data = None
    auth_path = Path(auth_file)
    if auth_path.exists():
        try:
            with open(auth_path, "r", encoding="utf-8") as f:
                auth_data = json.load(f)
            print(f"認証情報を読み込みました: {auth_file}")
        except Exception as e:
            print(f"認証情報の読み込みに失敗しました: {e}")
    else:
        print(f"認証ファイルが見つかりません: {auth_file}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--autoplay-policy=no-user-gesture-required',
                '--enable-audio-service-sandbox=false',
                '--disable-features=AudioServiceOutOfProcess',
                '--disable-blink-features=AutomationControlled',
            ]
        )

        # コンテキストを作成（検知回避設定）
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # 認証情報があればクッキーを設定
        if auth_data and "cookies" in auth_data:
            context.add_cookies(auth_data["cookies"])
            print("クッキーを設定しました")

        page = context.new_page()

        # WebDriverプロパティを削除（自動化検知回避）
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        print(f"Starting continuous ad capture from {url}")

        # 初回フラグ（ローカルストレージ設定用）
        first_load = True

        # 無限ループで広告を監視し続ける
        while True:
            video_process = None
            audio_process = None

            try:
                # ページを読み込む（初回または関連動画から）
                print("\nLoading page...")
                page.goto(url, wait_until='domcontentloaded')

                # 初回のみローカルストレージを設定
                if first_load and auth_data and "local_storage" in auth_data:
                    try:
                        for key, value in auth_data["local_storage"].items():
                            page.evaluate(f"localStorage.setItem({json.dumps(key)}, {json.dumps(value)})")
                        print("ローカルストレージを設定しました")
                        # リロードして認証情報を反映
                        page.reload(wait_until='domcontentloaded')
                        first_load = False
                    except Exception as e:
                        print(f"ローカルストレージの設定に失敗: {e}")
                        first_load = False

                # 動画が終わるまで、広告が出るたびにキャプチャ
                print("Watching video and monitoring for ads...")
                while True:
                    # 広告出現 or 動画終了を待つ（タイムアウト付き）
                    try:
                        result = page.evaluate("""
                                () => new Promise((resolve, reject) => {
                                    const video = document.querySelector('video');
                                    if (!video) {
                                        resolve('no_video');
                                        return;
                                    }

                                    let resolved = false;
                                    const doResolve = (value) => {
                                        if (!resolved) {
                                            resolved = true;
                                            resolve(value);
                                        }
                                    };

                                    // タイムアウト（2秒ごとにPythonに制御を戻す）
                                    setTimeout(() => doResolve('continue'), 2000);

                                    // 動画終了イベント
                                    video.addEventListener('ended', () => doResolve('video_ended'), { once: true });

                                    // 広告出現を監視
                                    const checkAd = () => {
                                        if (document.querySelector('.ad-showing')) {
                                            doResolve('ad_found');
                                        }
                                    };

                                    // 初回チェック
                                    checkAd();

                                    // MutationObserverで広告出現を監視
                                    const observer = new MutationObserver(checkAd);
                                    observer.observe(document.body, {
                                        subtree: true,
                                        attributes: true,
                                        attributeFilter: ['class']
                                    });
                            })
                        """)
                    except Exception:
                        # タイムアウトやエラーの場合は継続
                        result = 'continue'

                    if result == 'ad_found':
                        # 広告をキャプチャ
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_base = os.path.join(output_dir, timestamp)
                        output_path = output_base

                        suffix = 1
                        while os.path.exists(output_path):
                            output_path = f"{output_base}-{suffix}"
                            suffix += 1

                        os.makedirs(output_path, exist_ok=True)
                        print(f"Ad detected! Saving to {output_path}")

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

                        print("Capture complete, continuing to watch...")

                    elif result == 'video_ended':
                        print("Video ended")
                        break
                    elif result == 'continue':
                        # タイムアウト、ループを継続してシグナルチェック
                        continue
                    else:
                        print("Video element not found, skipping...")
                        break

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

        context.close()
        browser.close()
        print("Capture stopped")

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
