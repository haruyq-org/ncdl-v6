import tomllib
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config.toml"
DEFAULT_CONFIG = """[download]
output_path = "downloads"
default_resolution = "best"
"""

class Config:
    @staticmethod
    def ensure_config() -> Path:
        if not CONFIG_PATH.exists():
            CONFIG_PATH.write_text(DEFAULT_CONFIG, encoding="utf-8")

        return CONFIG_PATH

    @staticmethod
    def load() -> dict:
        Config.ensure_config()

        with CONFIG_PATH.open("rb") as file:
            return tomllib.load(file)

    @staticmethod
    def save_download(output_path: str, default_resolution: int | None) -> Path:
        output_path = output_path.replace("\\", "\\\\").replace("\"", "\\\"")
        default_resolution_value = f"{default_resolution}" if default_resolution is not None else "\"best\""
        CONFIG_PATH.write_text(
            "[download]\n"
            f"output_path = \"{output_path}\"\n"
            f"default_resolution = {default_resolution_value}\n",
            encoding="utf-8",
        )

        return CONFIG_PATH

    @staticmethod
    def get_download_config() -> dict:
        return Config.load().get("download", {})

    @staticmethod
    def get_output_path_value() -> str:
        return str(Config.get_download_config().get("output_path", "downloads"))

    @staticmethod
    def get_output_path() -> Path:
        output_path = Path(Config.get_output_path_value()).expanduser()

        if not output_path.is_absolute():
            output_path = ROOT_DIR / output_path

        return output_path

    @staticmethod
    def get_default_resolution() -> int | None:
        resolution = Config.get_download_config().get("default_resolution")
        if isinstance(resolution, int):
            return resolution

        return None
