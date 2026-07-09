import json
import subprocess
import os
import shutil
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
import httpx

ROOT_DIR = Path(__file__).resolve().parents[2]
BIN_DIR = ROOT_DIR / "bin"
YTD_PATH = BIN_DIR / ("yt-dlp.exe" if os.name == "nt" else "yt-dlp")
FFMPEG_PATH = BIN_DIR / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
FFPROBE_PATH = BIN_DIR / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
COOKIE_PATH = ROOT_DIR / "cookies.txt"

YTD_URL = {
    "nt": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe",
    "posix": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp",
}
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
RESOLUTION_OPTIONS = {
    1: 2160,
    2: 1440,
    3: 1080,
    4: 720,
    5: 480,
    6: 360,
    7: 240,
    8: 144,
}

class YTDUpdater:
    @staticmethod
    def download_file(url: str, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)

        with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as response:
            response.raise_for_status()

            with path.open("wb") as file:
                for chunk in response.iter_bytes():
                    file.write(chunk)
                    print(f"ダウンロード: {url} {file.tell() / 1024:.2f} KB", end="\r")

        return path

    @staticmethod
    def fetch_ytd() -> str:        
        url = YTD_URL.get(os.name)
        if url is None:
            raise RuntimeError("Unsupported OS")

        YTDUpdater.download_file(url, YTD_PATH)

        if os.name != "nt":
            YTD_PATH.chmod(YTD_PATH.stat().st_mode | 0o755)

        return str(YTD_PATH)

    @staticmethod
    def fetch_ffmpeg() -> str:        
        if os.name != "nt":
            raise RuntimeError("fetch_ffmpeg currently supports Windows only")

        with TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / "ffmpeg.zip"
            YTDUpdater.download_file(FFMPEG_URL, zip_path)

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

    @staticmethod
    def get_ytd_version() -> str:
        try:
            result = subprocess.run(
                [str(YTD_PATH), "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "Unknown"

    @staticmethod
    def update_ytd() -> str:
        try:
            result = subprocess.run(
                [str(YTD_PATH), "-U"],
                capture_output=True,
                text=True,
                check=True
            )
            
            output = result.stdout.strip()
            if "Updated yt-dlp" in output or "yt-dlp is up to date" in output:
                return True
            else:
                print("Unexpected output from yt-dlp update:", output)
                return False
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

class YTD:
    @staticmethod
    def get_output_template(output_path: Path) -> str:
        return str(output_path / "%(title)s.%(ext)s")

    @staticmethod
    def get_cookie_options(cookie_path: Path | None = COOKIE_PATH) -> list[str]:
        if cookie_path is not None and cookie_path.exists():
            return ["--cookies", str(cookie_path)]

        return []

    @staticmethod
    def get_js_runtime_options() -> list[str]:
        if shutil.which("node") is not None:
            return ["--js-runtimes", "node"]

        return []

    @staticmethod
    def get_title(url: str, cookie_path: Path | None = COOKIE_PATH) -> str | None:
        try:
            result = subprocess.run(
                [
                    str(YTD_PATH),
                    "--no-playlist",
                    "--windows-filenames",
                    *YTD.get_cookie_options(cookie_path),
                    *YTD.get_js_runtime_options(),
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

    @staticmethod
    def get_video_formats(url: str, resolution_height: int, cookie_path: Path | None = COOKIE_PATH) -> list[dict]:
        try:
            result = subprocess.run(
                [
                    str(YTD_PATH),
                    "--no-playlist",
                    "--windows-filenames",
                    *YTD.get_cookie_options(cookie_path),
                    *YTD.get_js_runtime_options(),
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

    @staticmethod
    def get_format_selector(format_info: dict) -> str:
        format_id = str(format_info["format_id"])
        if format_info.get("acodec") not in (None, "none"):
            return format_id

        return f"{format_id}+ba[ext=m4a]/{format_id}+ba/{format_id}"

    @staticmethod
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
                *YTD.get_cookie_options(cookie_path),
                *YTD.get_js_runtime_options(),
            ]
            output_command = [
                "-o",
                YTD.get_output_template(output_path),
                url,
            ]
            commands = []
            if resolution_height is not None:
                commands = [
                    [
                        *base_command,
                        "-f",
                        YTD.get_format_selector(format_info),
                        "--merge-output-format",
                        "mp4",
                        "--remux-video",
                        "mp4",
                        *output_command,
                    ]
                    for format_info in YTD.get_video_formats(url, resolution_height, cookie_path)
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

    @staticmethod
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
                    *YTD.get_cookie_options(cookie_path),
                    *YTD.get_js_runtime_options(),
                    "-f",
                    "ba/b",
                    "-x",
                    "--audio-format",
                    "mp3",
                    "--audio-quality",
                    "0",
                    "-o",
                    YTD.get_output_template(output_path),
                    url,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, RuntimeError):
            return False
