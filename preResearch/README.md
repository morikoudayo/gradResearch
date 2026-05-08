# YouTube Video Capture with Docker

XVFBとPipewireとPlaywrightとffmpegを使ってYouTube動画の再生をキャプチャするDockerコンテナです。

## 構成

- **XVFB**: 仮想ディスプレイサーバー
- **Pipewire**: オーディオサーバー（Pipewire-Pulseを含む）
- **Playwright**: ブラウザ自動化（Chromium）
- **ffmpeg**: ビデオ・オーディオキャプチャ

## ビルド方法

```bash
docker build -t youtube-capture .
```

## 使用方法

### 基本的な使い方（並列起動対応）

出力フォルダのみをマウントして実行します：

```bash
mkdir -p output
docker run --rm -v $(pwd)/output:/output youtube-capture \
  "https://www.youtube.com/watch?v=VIDEO_ID" \
  /output/video1.mp4 \
  30
```

### 並列実行の例

複数の動画を同時にキャプチャ：

```bash
mkdir -p output

# コンテナ1
docker run --rm -v $(pwd)/output:/output youtube-capture \
  "https://www.youtube.com/watch?v=VIDEO_ID_1" \
  /output/video1.mp4 \
  30 &

# コンテナ2
docker run --rm -v $(pwd)/output:/output youtube-capture \
  "https://www.youtube.com/watch?v=VIDEO_ID_2" \
  /output/video2.mp4 \
  30 &

# コンテナ3
docker run --rm -v $(pwd)/output:/output youtube-capture \
  "https://www.youtube.com/watch?v=VIDEO_ID_3" \
  /output/video3.mp4 \
  30 &

wait
echo "All captures completed!"
```

### パラメータ

1. YouTube動画のURL（必須）
2. 出力ファイル名（オプション、デフォルト: output.mp4）
3. キャプチャ時間（秒）（オプション、デフォルト: 60）

### 重要なポイント

- **出力パスは `/output/` から始める必要があります**（ホストの`output`フォルダにマウントされます）
- 各コンテナは独立して動作し、互いに干渉しません
- 並列実行時は異なる出力ファイル名を指定してください

## 注意事項

- コンテナ内でブラウザが実際に動画を再生するため、ネットワーク接続が必要です
- 動画の長さがキャプチャ時間より短い場合は、残りの時間は静止画になります
- 一部の動画では地域制限や年齢制限により再生できない場合があります
- 並列実行時はシステムリソース（CPU、メモリ、ネットワーク帯域）に注意してください

## トラブルシューティング

### オーディオがキャプチャされない場合

Pipewireの設定を確認してください。必要に応じて`entrypoint.sh`の待機時間を調整してください。

### ブラウザが起動しない場合

メモリ不足の可能性があります。Dockerに割り当てるメモリを増やしてください。

```bash
docker run --rm --memory=4g -v $(pwd)/output:/output youtube-capture "URL" /output/video.mp4
```

### 並列実行時のリソース不足

同時に実行するコンテナの数を減らすか、各コンテナに割り当てるリソースを調整してください。

```bash
docker run --rm --cpus=2 --memory=2g -v $(pwd)/output:/output youtube-capture "URL" /output/video.mp4
```
