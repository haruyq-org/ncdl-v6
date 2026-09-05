import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from textual.widgets import Static

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ui.app import NCDLApp


@patch.object(NCDLApp, "update_logo_animation", lambda self: None)
class AppTests(unittest.IsolatedAsyncioTestCase):
    @patch("ui.app.get_ytd_version", return_value="test")
    @patch("ui.app.config.get_default_resolution", return_value=None)
    @patch("ui.app.config.get_output_path", return_value=Path("downloads"))
    @patch("ui.app.ytd.get_cookie_options", return_value=[])
    @patch("ui.app.ytd.get_title", return_value="動画 [test]")
    @patch("ui.app.spotdl.download", return_value=False)
    @patch("ui.app.ytd.download", side_effect=[False, False, False, OSError("保存先 [test] に書き込めません"), True])
    async def test_download_failures_notify_and_continue_queue(self, download, spotify, _title, _cookies, output_path, _resolution, _version) -> None:
        app = NCDLApp()
        jobs = (
            ("MP4", "https://example.com/mp4"),
            ("MP3", "https://example.com/mp3"),
            ("GIF", "https://example.com/gif"),
            ("MP3", "https://open.spotify.com/track/example"),
            ("MP4", "https://example.com/exception"),
            ("MP4", "https://example.com/config"),
            ("MP4", "https://example.com/success"),
        )

        async with app.run_test(notifications=True) as pilot:
            output_path.side_effect = [Path("downloads")] * 5 + [ValueError("保存先の設定を確認してください"), Path("downloads")]
            for mode, uri in jobs:
                app.mode = mode
                app.handle_input_submit(uri)

            while app.workers:
                await app.workers.wait_for_complete()
            await pilot.pause()

            self.assertIsNone(app.active_job)
            self.assertFalse(app.download_queue)
            notifications = list(app._notifications)
            self.assertEqual(len(notifications), 6)
            self.assertGreater(len(app.query("Toast")), 0)
            for notification, (_, uri) in zip(notifications, jobs):
                self.assertEqual(notification.severity, "error")
                self.assertEqual(notification.title, "ダウンロード失敗")
                self.assertIn(uri, notification.message)
                self.assertFalse(notification.markup)
            self.assertIn("保存先 [test] に書き込めません", notifications[4].message)
            self.assertIn("保存先の設定を確認してください", notifications[5].message)
            self.assertEqual(
                [call.kwargs["output_format"] for call in download.call_args_list],
                ["mp4", "mp3", "gif", "mp4", "mp4"],
            )
            self.assertEqual(download.call_args.args[0], jobs[-1][1])
            spotify.assert_called_once_with(jobs[3][1], Path("downloads"))

    @patch("ui.app.get_ytd_version", return_value="test")
    @patch("ui.app.config.get_default_resolution", return_value=None)
    @patch("ui.app.config.get_output_path", return_value=Path("downloads"))
    @patch("ui.app.ytd.get_cookie_options", return_value=[])
    @patch("ui.app.ytd.get_title", return_value="動画 [test]")
    @patch("ui.app.spotdl.download", return_value=True)
    @patch("ui.app.ytd.download", return_value=True)
    async def test_cookie_status_tracks_available_and_active_downloads(self, _download, _spotify, _title, cookies, _output_path, _resolution, _version) -> None:
        app = NCDLApp()

        async with app.run_test() as pilot:
            state = app.query_one("#state", Static)
            self.assertIn("Cookieなし", str(state.content))
            cookies.return_value = ["--cookies", "cookies.txt"]
            app.update_mode_view()
            self.assertIn("Cookieあり", str(state.content))

            for uri, expected in (
                ("https://example.com/video", "Cookie使用中"),
                ("https://open.spotify.com/track/example", "Cookie対象外"),
            ):
                app.handle_input_submit(uri)
                self.assertIn(expected, str(state.content))
                while app.workers:
                    await app.workers.wait_for_complete()
                await pilot.pause()
                self.assertIn("Cookieあり", str(state.content))

            cookies.return_value = []
            app.handle_input_submit("https://example.com/no-cookie")
            self.assertIn("Cookieなし", str(state.content))
            while app.workers:
                await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertIn("Cookieなし", str(state.content))
            self.assertFalse(list(app._notifications))


if __name__ == "__main__":
    unittest.main()
