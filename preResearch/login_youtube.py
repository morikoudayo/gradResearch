#!/usr/bin/env python3
"""
ホスト機でYoutubeにログインして認証情報をJSONファイルに保存するスクリプト
"""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright

def login_youtube(output_file="auth/auth.json"):
    """Youtubeにログインして認証情報を保存"""
    with sync_playwright() as p:
        # ブラウザを起動（ヘッドレスモードOFF、検知回避設定）
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
            ]
        )
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # WebDriverプロパティを削除
        page = context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        print("Youtubeを開きます...")
        page.goto("https://www.youtube.com")

        print("\n" + "="*60)
        print("ブラウザウィンドウでYoutubeにログインしてください")
        print("ログインが完了したら、このターミナルでEnterキーを押してください")
        print("="*60 + "\n")

        # ユーザーがログインするまで待機
        input("ログイン完了後、Enterキーを押してください: ")

        # 認証情報を取得
        cookies = context.cookies()
        local_storage = page.evaluate("""
            () => {
                const items = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    items[key] = localStorage.getItem(key);
                }
                return items;
            }
        """)

        # JSONファイルに保存
        auth_data = {
            "cookies": cookies,
            "local_storage": local_storage
        }

        output_path = Path(output_file)
        # ディレクトリを作成
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(auth_data, f, indent=2, ensure_ascii=False)

        print(f"\n認証情報を {output_path.absolute()} に保存しました")

        browser.close()

if __name__ == "__main__":
    import sys
    output_file = sys.argv[1] if len(sys.argv) > 1 else "auth/auth.json"

    try:
        login_youtube(output_file)
        print("\n✓ 認証情報の保存が完了しました")
        print("  これでコンテナでYoutubeにログインした状態で実行できます")
    except KeyboardInterrupt:
        print("\n中断されました")
        sys.exit(1)
