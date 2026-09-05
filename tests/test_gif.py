import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ui.app import NCDLApp
from utils import ytd

class GifTests(unittest.IsolatedAsyncioTestCase):
    @patch("ui.app.NCDLApp.update_logo_animation")
    @patch("ui.app.get_ytd_version", return_value="test")
    async def test_mode_cycles_through_gif(self, _get_ytd_version, _update_logo_animation) -> None:
        app = NCDLApp()

        async with app.run_test() as pilot:
            await pilot.press("tab")
            self.assertEqual(app.mode, "MP3")
            await pilot.press("tab")
            self.assertEqual(app.mode, "GIF")
            await pilot.press("tab")
            self.assertEqual(app.mode, "MP4")

    @patch("utils.ytd.get_js_runtime_options", return_value=[])
    @patch("utils.ytd.subprocess.run")
    def test_download_gif_reencodes_video(self, run, _get_js_runtime_options) -> None:
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "downloads"

            self.assertTrue(ytd.download_gif("https://example.com/video", output_path, None))

        command = run.call_args.args[0]
        self.assertEqual(command[command.index("--recode-video") + 1], "gif")
        self.assertEqual(command[command.index("-f") + 1], "bv*/b")
        self.assertEqual(command[-1], "https://example.com/video")

if __name__ == "__main__":
    unittest.main()
