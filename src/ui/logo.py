import tomllib
from pathlib import Path
from rich.text import Text

LOGO_PRIMARY = "#4fd8ff"
LOGO_SECONDARY = "#8fc9d9"
LOGO_SHADOW = "#16313a"
LOGO_VERSION = "#3bbfe8"

LOGO_LINES = [
    "█▄  █ █▀▀▀ █▀▀▄ █      █  █  ▄▀▀ ",
    "█ ▀▄█ █    █  █ █      █  █  █▀▀▄",
    "▀   ▀ ▀▀▀▀ ▀▀▀  ▀▀▀▀    ▀▀    ▀▀ ",
]

def get_app_version() -> str:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"

    try:
        with pyproject.open("rb") as file:
            return tomllib.load(file)["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return "0.0.0"

def draw_logo_char(logo: Text, char: str, color: str, *, bold: bool = True) -> None:
    weight = "bold " if bold else ""
    match char:
        case "_":
            logo.append(" ", style=f"on {LOGO_SHADOW}")
        case "^":
            logo.append("▀", style=f"{weight}{color} on {LOGO_SHADOW}")
        case "~":
            logo.append("▀", style=LOGO_SHADOW)
        case ",":
            logo.append("▄", style=LOGO_SHADOW)
        case "█":
            logo.append("▀", style=f"{weight}{color} on {color}")
        case " ":
            logo.append(" ")
        case _:
            logo.append(char, style=f"{weight}{color}")

def draw_logo_part(logo: Text, line: str, color: str, *, bold: bool = True) -> None:
    for char in line:
        draw_logo_char(logo, char, color, bold=bold)

def render_ncdl_logo() -> Text:
    logo = Text(no_wrap=True)
    version = get_app_version()
    logo_width = max(len(line) for line in LOGO_LINES)

    logo.append(version.rjust(logo_width), style=f"bold {LOGO_VERSION}")
    logo.append("\n")
    logo.append(" " * logo_width)
    logo.append("\n")

    for i, line in enumerate(LOGO_LINES):
        color = LOGO_PRIMARY if i == 0 else LOGO_SECONDARY
        draw_logo_part(logo, line, color)

        if i < len(LOGO_LINES) - 1:
            logo.append("\n")

    return logo

def render_mimo_logo() -> Text:
    return render_ncdl_logo()
