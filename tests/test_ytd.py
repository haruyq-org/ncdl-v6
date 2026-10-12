import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils import ytd


class YtdTests(unittest.TestCase):
    @patch("utils.ytd.get_js_runtime_options", return_value=[])
    @patch("utils.ytd.subprocess.run")
    def test_twitter_authentication_failure_retries_without_cookies(self, run, _runtime) -> None:
        url = "https://x.com/example/status/123?s=20"
        formats = [{"format_id": "video", "height": 720, "vcodec": "avc1", "acodec": "none"}]

        def run_command(command, **kwargs):
            if "--cookies" in command:
                raise subprocess.CalledProcessError(1, command, stderr="ERROR: [twitter] 123: Error(s) while querying API: Could not authenticate you")

            stdout = json.dumps({"formats": formats}) if "--dump-single-json" in command else "title\n"
            return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

        run.side_effect = run_command
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir)
            cookie_path = output_path / "cookies.txt"
            cookie_path.write_text("cookies", encoding="utf-8")
            self.assertEqual(ytd.get_title(url, cookie_path), "title")
            self.assertEqual(ytd.get_video_formats(url, 720, cookie_path), formats)
            for output_format in ("mp4", "gif"):
                for resolution_height in (None, 720):
                    with self.subTest(output_format=output_format, resolution_height=resolution_height):
                        self.assertTrue(ytd.download(url, output_path, output_format, cookie_path, resolution_height))

            self.assertEqual(cookie_path.read_text(encoding="utf-8"), "cookies")

        calls = run.call_args_list
        self.assertEqual(len(calls), 16)
        for first, retry in zip(calls[::2], calls[1::2]):
            command = first.args[0]
            cookie_index = command.index("--cookies")
            self.assertEqual(retry.args[0], command[:cookie_index] + ["--no-cookies"] + command[cookie_index + 2:])
            self.assertEqual(retry.kwargs, first.kwargs)

    @patch("utils.ytd.subprocess.run")
    def test_other_failures_are_not_retried_without_cookies(self, run) -> None:
        command = ["yt-dlp", "--cookies", "cookies.txt", "https://x.com/example/status/123"]
        for stderr in (None, "ERROR: [twitter] HTTP Error 403", "ERROR: [youtube] Could not authenticate you"):
            with self.subTest(stderr=stderr):
                run.reset_mock()
                error = subprocess.CalledProcessError(1, command, stderr=stderr)
                run.side_effect = error
                with self.assertRaises(subprocess.CalledProcessError) as caught:
                    ytd.run_ytd(command)

                self.assertIs(caught.exception, error)
                run.assert_called_once_with(command, capture_output=True, text=True, check=True)

    @patch("utils.ytd.subprocess.run")
    def test_twitter_retry_is_limited_to_once(self, run) -> None:
        for cookie_options, attempts in (([], 1), (["--cookies", "cookies.txt"], 2)):
            with self.subTest(cookie_options=cookie_options):
                run.reset_mock()
                command = ["yt-dlp", *cookie_options, "https://x.com/example/status/123"]
                run.side_effect = subprocess.CalledProcessError(1, command, stderr="ERROR: [twitter] Could not authenticate you")
                with self.assertRaises(subprocess.CalledProcessError):
                    ytd.run_ytd(command)

                self.assertEqual(run.call_count, attempts)


if __name__ == "__main__":
    unittest.main()
