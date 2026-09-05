# ncdl-v6

ncdl-v6は、Textualで構成されたyt-dlpとspotdlのラッパーUIです。
このアプリでは、より直感的な方法で様々な動画・音声をダウンロードできます。

<img src="./assets/Screenshot 2026-07-16 023225.png" width="700" height="400" />

## 実行

```bash
uv run python src/main.py
```

### CLI

```bash
uv run python src/main.py download "https://www.youtube.com/watch?v=VIDEO_ID"
uv run python src/main.py download "https://www.youtube.com/watch?v=VIDEO_ID" -r 1080p -f mkv -o downloads
uv run python src/main.py convert "input.mp3" -f wav
uv run python src/main.py convert "input.mp4" -o "output.webm"
```

## ビルド

> Windows

```bash
.\build.bat
```

> Linux
```
Soon
```

## ライセンス

このプロジェクトは[MIT License](./LICENSE)で公開されています。
