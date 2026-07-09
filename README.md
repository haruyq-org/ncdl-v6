# ncdl-v6

Windows向けの、Textualで作られたyt-dlpのダウンロードUIです。

## 実行

```powershell
uv run python src/main.py
```

初回起動時にyt-dlpとFFmpegを自動取得します。

## テスト

```powershell
uv run python -m unittest discover -s tests
```

## ビルド

```powershell
.\build.bat
```

実行ファイルは`dist/ncdl.exe`に作成されます。

## 構成

- `src/ui`: アプリ画面、設定画面、コマンド入力
- `src/utils`: 設定、パス、外部ツール、ダウンロード処理
