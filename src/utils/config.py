import json
import tomllib
from pathlib import Path

from utils.paths import get_app_dir, get_config_dir

ROOT_DIR = get_app_dir()
CONFIG_DIR = get_config_dir()
CONFIG_PATH = CONFIG_DIR / "config.toml"
DEFAULT_CONFIG = """[download]
output_path = "downloads"
default_resolution = "best"
default_format = "mp4"
"""


def ensure_config() -> Path:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(DEFAULT_CONFIG, encoding="utf-8")

    return CONFIG_PATH


def load() -> dict:
    ensure_config()

    with CONFIG_PATH.open("rb") as file:
        return tomllib.load(file)


def save_download(output_path: str, default_resolution: int | None) -> Path:
    output_path = json.dumps(output_path, ensure_ascii=False)
    default_format = json.dumps(get_default_format(), ensure_ascii=False)
    default_resolution_value = f"{default_resolution}" if default_resolution is not None else "\"best\""
    CONFIG_PATH.write_text(
        "[download]\n"
        f"output_path = {output_path}\n"
        f"default_resolution = {default_resolution_value}\n"
        f"default_format = {default_format}\n",
        encoding="utf-8",
    )

    return CONFIG_PATH


def get_download_config() -> dict:
    return load().get("download", {})


def get_output_path_value() -> str:
    return str(get_download_config().get("output_path", "downloads"))


def get_output_path() -> Path:
    output_path = Path(get_output_path_value()).expanduser()

    if not output_path.is_absolute():
        output_path = ROOT_DIR / output_path

    return output_path


def get_default_resolution() -> int | None:
    resolution = get_download_config().get("default_resolution")
    if isinstance(resolution, int):
        return resolution

    return None


def get_default_format() -> str:
    return str(get_download_config().get("default_format", "mp4"))
