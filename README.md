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


```bash
.\build.bat
```

MSIも作成する場合は、uvと.NET 8 SDKをインストールして次を実行します。WiXは[ツール定義](./.config/dotnet-tools.json)から自動で復元します。

```powershell
.\build-installer.ps1
```

`dist/ncdl-バージョン-windows-x64.msi`を出力します。EXEを作成済みの場合は`-SkipBuild`を指定できます。

### GitHub Actionsでのリリース

`src/__version__.py`と`pyproject.toml`のバージョンを同じ`major.minor.patch`に更新し、`uv lock`で`uv.lock`も更新してください。変更をコミットしてから、対応する`v`付きタグをpushします。例:

```bash
git tag v1.2.3
git push origin v1.2.3
```

[Windows release](./.github/workflows/release.yml)がテスト・ビルド・インストールと上書き更新の検証を行い、GitHub ReleaseにMSIと単体EXEを添付します。タグとソースのバージョンが異なる場合はリリースを停止します。
上書き更新の識別に使用するため、[インストーラー定義](./installer/ncdl.wxs)の`UpgradeCode`とコンポーネントの`Guid`は変更しないでください。

## ライセンス

このプロジェクトは[MIT License](./LICENSE)で公開されています。
