import tomllib
from pathlib import Path
from rich.text import Text
from __version__ import __version__

LOGO_PRIMARY = "#4fd8ff"
LOGO_SECONDARY = "#a6efff"
LOGO_HIGHLIGHT = "#e2fbff"
LOGO_SHADOW = "#16313a"
LOGO_VERSION = "#6de8ff"

LOGO_LINES = [
    "█▄  █ █▀▀▀ █▀▀▄ █      █  █  ▄▀▀ ",
    "█ ▀▄█ █    █  █ █      █  █  █▀▀▄",
    "▀   ▀ ▀▀▀▀ ▀▀▀  ▀▀▀▀    ▀▀    ▀▀ ",
]

def draw_logo_char(
    logo: Text,
    char: str,
    color: str,
    *,
    shadow: str = LOGO_SHADOW,
    bold: bool = True,
) -> None:
    weight = "bold " if bold else ""
    match char:
        case "_":
            logo.append(" ", style=f"on {shadow}")
        case "^":
            logo.append("▀", style=f"{weight}{color} on {shadow}")
        case "~":
            logo.append("▀", style=shadow)
        case ",":
            logo.append("▄", style=shadow)
        case "█":
            logo.append("▀", style=f"{weight}{color} on {color}")
        case " ":
            logo.append(" ")
        case _:
            logo.append(char, style=f"{weight}{color}")

def draw_logo_part(logo: Text, line: str, color: str, frame: int, *, bold: bool = True) -> None:
    scan = (frame * 3) % (len(line) + 8) - 4

    for x, char in enumerate(line):
        if char != " " and abs(x - scan) <= 1:
            draw_logo_char(logo, char, LOGO_HIGHLIGHT, shadow="#245766", bold=bold)
        elif char != " " and (x + frame) % 19 == 0:
            draw_logo_char(logo, char, LOGO_PRIMARY, shadow=LOGO_SHADOW, bold=False)
        else:
            draw_logo_char(logo, char, color, shadow=LOGO_SHADOW, bold=bold)

def render_ncdl_logo(frame: int = 0) -> Text:
    logo = Text(no_wrap=True)
    version = __version__
    logo_width = max(len(line) for line in LOGO_LINES)

    logo.append(version.rjust(logo_width), style=f"bold {LOGO_VERSION}")
    logo.append("\n")
    logo.append(" " * logo_width)
    logo.append("\n")

    for i, line in enumerate(LOGO_LINES):
        color = LOGO_PRIMARY if i == 0 else LOGO_SECONDARY
        draw_logo_part(logo, line, color, frame + i)

        if i < len(LOGO_LINES) - 1:
            logo.append("\n")

    return logo

def render_mimo_logo() -> Text:
    return render_ncdl_logo()
