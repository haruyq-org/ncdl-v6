import json
import shutil
import subprocess
from pathlib import Path

from utils.paths import get_app_dir
from utils.tools import FFMPEG_PATH, YTD_PATH

COOKIE_PATH = get_app_dir() / "cookies.txt"


def get_output_template(output_path: Path) -> str:
    return str(output_path / "%(title)s.%(ext)s")


def get_cookie_options(cookie_path: Path | None = COOKIE_PATH) -> list[str]:
    if cookie_path is not None and cookie_path.exists():
        return ["--cookies", str(cookie_path)]

    return []


def get_js_runtime_options() -> list[str]:
    if shutil.which("node") is not None:
        return ["--js-runtimes", "node"]

    return []


def get_title(url: str, cookie_path: Path | None = COOKIE_PATH) -> str | None:
    try:
        result = subprocess.run(
            [
                str(YTD_PATH),
                "--no-playlist",
                "--windows-filenames",
                *get_cookie_options(cookie_path),
                *get_js_runtime_options(),
                "--print",
                "%(title)s",
                url,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().splitlines()[0]
    except (subprocess.CalledProcessError, FileNotFoundError, RuntimeError, IndexError):
        return None


def get_video_formats(url: str, resolution_height: int, cookie_path: Path | None = COOKIE_PATH) -> list[dict]:
    try:
        result = subprocess.run(
            [
                str(YTD_PATH),
                "--no-playlist",
                "--windows-filenames",
                *get_cookie_options(cookie_path),
                *get_js_runtime_options(),
                "--dump-single-json",
                url,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        info = json.loads(result.stdout)
        formats = info.get("formats", [])
        candidates = [
            format_info for format_info in formats
            if isinstance(format_info.get("height"), int)
            and format_info.get("vcodec") not in (None, "none")
            and format_info.get("format_id") is not None
        ]

        if not candidates:
            return []

        def sort_key(format_info: dict) -> tuple[int, int, int, int]:
            vcodec = str(format_info.get("vcodec") or "")
            try:
                fps = int(float(format_info.get("fps") or 0))
            except (TypeError, ValueError):
                fps = 0

            return (
                abs(format_info["height"] - resolution_height),
                0 if format_info.get("ext") == "mp4" else 1,
                0 if vcodec.startswith("avc1") else 1,
                -int(fps),
            )

        return sorted(candidates, key=sort_key)
    except (subprocess.CalledProcessError, FileNotFoundError, RuntimeError, json.JSONDecodeError):
        return []


def get_format_selector(format_info: dict) -> str:
    format_id = str(format_info["format_id"])
    if format_info.get("acodec") not in (None, "none"):
        return format_id

    return f"{format_id}+ba[ext=m4a]/{format_id}+ba/{format_id}"


def download_mp4(
    url: str,
    output_path: Path,
    cookie_path: Path | None = COOKIE_PATH,
    resolution_height: int | None = None,
) -> bool:
    try:
        output_path.mkdir(parents=True, exist_ok=True)

        base_command = [
            str(YTD_PATH),
            "--ffmpeg-location",
            str(FFMPEG_PATH.parent),
            "--no-playlist",
            "--windows-filenames",
            "--force-overwrites",
            *get_cookie_options(cookie_path),
            *get_js_runtime_options(),
        ]
        output_command = [
            "-o",
            get_output_template(output_path),
            url,
        ]
        if resolution_height is not None:
            commands = [
                [
                    *base_command,
                    "-f",
                    get_format_selector(format_info),
                    "--merge-output-format",
                    "mp4",
                    "--remux-video",
                    "mp4",
                    *output_command,
                ]
                for format_info in get_video_formats(url, resolution_height, cookie_path)
            ]

            if not commands:
                return False
        else:
            commands = [
                [
                    *base_command,
                    "-f",
                    "bv*[ext=mp4][vcodec^=avc1]+ba[ext=m4a]/bv*[vcodec^=avc1]+ba/bv*+ba/b",
                    "--merge-output-format",
                    "mp4",
                    "--remux-video",
                    "mp4",
                    *output_command,
                ],
                [
                    *base_command,
                    "--extractor-args",
                    "youtube:player_client=android",
                    "-f",
                    "b[ext=mp4]/b",
                    "--remux-video",
                    "mp4",
                    *output_command,
                ],
            ]

        for command in commands:
            try:
                subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                return True
            except subprocess.CalledProcessError:
                pass

        return False
    except (FileNotFoundError, RuntimeError):
        return False


def download_mp3(url: str, output_path: Path, cookie_path: Path | None = COOKIE_PATH) -> bool:
    try:
        output_path.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            [
                str(YTD_PATH),
                "--ffmpeg-location",
                str(FFMPEG_PATH.parent),
                "--no-playlist",
                "--windows-filenames",
                "--force-overwrites",
                *get_cookie_options(cookie_path),
                *get_js_runtime_options(),
                "-f",
                "ba/b",
                "-x",
                "--audio-format",
                "mp3",
                "--audio-quality",
                "0",
                "-o",
                get_output_template(output_path),
                url,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, RuntimeError):
        return False
