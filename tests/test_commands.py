import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ui.commands import (
    RESOLUTION_OPTIONS,
    is_resolution_command,
    is_resolution_number_match,
    parse_resolution_command,
)

class CommandTests(unittest.TestCase):
    def test_parse_resolution_command(self) -> None:
        self.assertEqual(
            parse_resolution_command("/r 3 https://example.com/video"),
            ("https://example.com/video", 1080),
        )

    def test_parse_resolution_command_requires_arguments(self) -> None:
        with self.assertRaises(ValueError) as error:
            parse_resolution_command("/r 3")

        self.assertEqual(str(error.exception), "使い方: /r 番号 URL")

    def test_parse_resolution_command_rejects_unknown_number(self) -> None:
        with self.assertRaises(ValueError) as error:
            parse_resolution_command("/r 99 https://example.com/video")

        options = ", ".join(f"{number}={height}p" for number, height in RESOLUTION_OPTIONS.items())
        self.assertEqual(str(error.exception), f"解像度番号は {options} から指定してください。")

    def test_resolution_command_helpers(self) -> None:
        self.assertTrue(is_resolution_command("/res"))
        self.assertFalse(is_resolution_command("/unknown"))
        self.assertTrue(is_resolution_number_match("/r", 1))
        self.assertTrue(is_resolution_number_match("/r 3", 3))
        self.assertFalse(is_resolution_number_match("/r 3", 2))

if __name__ == "__main__":
    unittest.main()
