import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx

from utils.paths import get_data_dir, get_project_dir, is_frozen

ROOT_DIR = get_data_dir() if is_frozen() else get_project_dir()
BIN_DIR = ROOT_DIR / "bin"
YTD_PATH = BIN_DIR / ("yt-dlp.exe" if os.name == "nt" else "yt-dlp")
FFMPEG_PATH = BIN_DIR / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
FFPROBE_PATH = BIN_DIR / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
SPOTDL_PATH = BIN_DIR / ("spotdl.exe" if os.name == "nt" else "spotdl")

YTD_URL = {
    "nt": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe",
    "posix": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp",
}
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
SPOTDL_RELEASE_URL = "https://api.github.com/repos/spotDL/spotify-downloader/releases/latest"


def download_file(url: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as response:
        response.raise_for_status()

        with path.open("wb") as file:
            for chunk in response.iter_bytes():
                file.write(chunk)
                print(f"ダウンロード: {url} {file.tell() / 1024:.2f} KB", end="\r")

    return path


def fetch_ytd() -> str:
    url = YTD_URL.get(os.name)
    if url is None:
        raise RuntimeError("Unsupported OS")

    download_file(url, YTD_PATH)

    if os.name != "nt":
        YTD_PATH.chmod(YTD_PATH.stat().st_mode | 0o755)

    return str(YTD_PATH)


def fetch_ffmpeg() -> str:
    if os.name != "nt":
        raise RuntimeError("fetch_ffmpeg currently supports Windows only")

    with TemporaryDirectory() as temp_dir:
        zip_path = Path(temp_dir) / "ffmpeg.zip"
        download_file(FFMPEG_URL, zip_path)

        with zipfile.ZipFile(zip_path) as archive:
            for file_name, target_path in (
                ("ffmpeg.exe", FFMPEG_PATH),
                ("ffprobe.exe", FFPROBE_PATH),
            ):
                archive_name = next(
                    (name for name in archive.namelist() if name.endswith(f"/bin/{file_name}")),
                    None,
                )
                if archive_name is None:
                    raise FileNotFoundError(f"{file_name} was not found in archive")

                target_path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(archive_name) as source, target_path.open("wb") as target:
                    shutil.copyfileobj(source, target)

    return str(FFMPEG_PATH)


def fetch_spotdl() -> str:
    suffix = "-win32.exe" if os.name == "nt" else "-darwin" if sys.platform == "darwin" else "-linux"
    response = httpx.get(SPOTDL_RELEASE_URL, follow_redirects=True, timeout=60.0)
    response.raise_for_status()
    asset = next(
        (asset for asset in response.json()["assets"] if asset["name"].endswith(suffix)),
        None,
    )
    if asset is None:
        raise FileNotFoundError("spotDL executable was not found in the latest release")

    download_file(asset["browser_download_url"], SPOTDL_PATH)

    if os.name != "nt":
        SPOTDL_PATH.chmod(SPOTDL_PATH.stat().st_mode | 0o755)

    return str(SPOTDL_PATH)


def ensure_tools(*, ytd: bool = True, spotdl: bool = True) -> None:
    if ytd and not YTD_PATH.exists():
        fetch_ytd()
    if not FFMPEG_PATH.exists() or not FFPROBE_PATH.exists():
        fetch_ffmpeg()
    if spotdl and not SPOTDL_PATH.exists():
        fetch_spotdl()


def get_ytd_version() -> str:
    try:
        result = subprocess.run(
            [str(YTD_PATH), "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "Unknown"


def update_ytd() -> bool:
    try:
        result = subprocess.run(
            [str(YTD_PATH), "-U"],
            capture_output=True,
            text=True,
            check=True,
        )

        output = result.stdout.strip()
        if "Updated yt-dlp" in output or "yt-dlp is up to date" in output:
            return True

        print("Unexpected output from yt-dlp update:", output)
        return False
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
