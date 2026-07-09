from textual.suggester import Suggester

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
RESOLUTION_COMMAND = "/r"
RESOLUTION_COMMAND_ALIASES = (RESOLUTION_COMMAND, "/resolution")
RESOLUTION_DESCRIPTION = "解像度を番号で指定してMP4をダウンロード"

class CommandSuggester(Suggester):
    async def get_suggestion(self, value: str) -> str | None:
        if not value.startswith("/"):
            return None

        for alias in RESOLUTION_COMMAND_ALIASES:
            if alias.startswith(value):
                return f"{alias} "

        command = value.split(maxsplit=1)[0]
        if command in RESOLUTION_COMMAND_ALIASES and value.startswith(f"{command} "):
            argument = value.removeprefix(f"{command} ")
            if " " in argument:
                return None

            for number in RESOLUTION_OPTIONS:
                suggestion = str(number)
                if suggestion.startswith(argument):
                    return f"{command} {suggestion} "

        return None

def normalize_resolution(value: int | None) -> int | None:
    return value if value in RESOLUTION_OPTIONS.values() else None

def is_resolution_command(command: str) -> bool:
    return any(alias.startswith(command) for alias in RESOLUTION_COMMAND_ALIASES)

def is_resolution_number_match(value: str, number: int) -> bool:
    parts = value.split(maxsplit=2)
    if len(parts) < 2:
        return number == next(iter(RESOLUTION_OPTIONS))

    return str(number).startswith(parts[1])

def parse_resolution_command(command: str) -> tuple[str, int]:
    parts = command.split(maxsplit=2)
    if len(parts) != 3:
        raise ValueError("使い方: /r 番号 URL")

    try:
        number = int(parts[1])
        resolution_height = RESOLUTION_OPTIONS[number]
    except (ValueError, KeyError):
        options = ", ".join(f"{number}={height}p" for number, height in RESOLUTION_OPTIONS.items())
        raise ValueError(f"解像度番号は {options} から指定してください。") from None

    return parts[2].strip(), resolution_height
