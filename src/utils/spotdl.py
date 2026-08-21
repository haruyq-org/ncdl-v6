import subprocess
from pathlib import Path
from urllib.parse import urlparse

from utils.tools import FFMPEG_PATH, SPOTDL_PATH


def is_spotify_url(url: str) -> bool:
    hostname = urlparse(url).hostname
    return hostname in ("spoti.fi", "spotify.link", "spotify.com") or (
        hostname is not None and hostname.endswith(".spotify.com")
    )


def download(url: str, output_path: Path) -> bool:
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                str(SPOTDL_PATH),
                "download",
                url,
                "--format",
                "mp3",
                "--ffmpeg",
                str(FFMPEG_PATH),
                "--output",
                str(output_path / "{artists} - {title}.{output-ext}"),
                "--overwrite",
                "force",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, RuntimeError):
        return False
