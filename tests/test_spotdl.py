import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils import spotdl


class SpotdlTests(unittest.TestCase):
    def test_spotify_url_detection(self) -> None:
        self.assertTrue(spotdl.is_spotify_url("https://open.spotify.com/track/example"))
        self.assertTrue(spotdl.is_spotify_url("https://spotify.link/example"))
        self.assertTrue(spotdl.is_spotify_url("https://spoti.fi/example"))
        self.assertFalse(spotdl.is_spotify_url("https://spotify.com.example.com/track/example"))

    @patch("utils.spotdl.subprocess.run")
    def test_download_uses_spotdl(self, run) -> None:
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "downloads"

            self.assertTrue(spotdl.download("https://open.spotify.com/track/example", output_path))

        command = run.call_args.args[0]
        self.assertEqual(command[1:3], ["download", "https://open.spotify.com/track/example"])
        self.assertEqual(command[command.index("--format") + 1], "mp3")
        self.assertEqual(command[command.index("--ffmpeg") + 1], str(spotdl.FFMPEG_PATH))


if __name__ == "__main__":
    unittest.main()
