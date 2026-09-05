import io
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import cli
from utils import config, convert, ytd


class CliTests(unittest.TestCase):
    @patch("cli.ensure_tools")
    def test_cli_output_uses_utf8_with_legacy_streams(self, ensure_tools) -> None:
        cases = (
            (["--help"], 0, "動画のダウンロードとファイルの変換"),
            (["download", "--help"], 0, "動画のURL"),
            (["convert", "--help"], 0, "変換するファイル"),
            (["download", "invalid"], 2, "httpまたはhttpsの動画URLを指定してください。"),
        )
        for args, exit_code, message in cases:
            with self.subTest(args=args), io.TextIOWrapper(io.BytesIO(), encoding="cp1252") as stdout, io.TextIOWrapper(io.BytesIO(), encoding="cp1252") as stderr:
                with redirect_stdout(stdout), redirect_stderr(stderr), self.assertRaises(SystemExit) as error:
                    cli.main(args)

                self.assertEqual(error.exception.code, exit_code)
                output = stdout if exit_code == 0 else stderr
                output.flush()
                self.assertIn(message, output.buffer.getvalue().decode("utf-8"))

        ensure_tools.assert_not_called()

    @patch("cli.ensure_tools")
    @patch("cli.ytd.download", return_value=True)
    def test_download_defaults_and_overrides(self, download, ensure_tools) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "config.toml"
            config_path.write_text(
                '[download]\noutput_path = "saved"\ndefault_resolution = 720\ndefault_format = "webm"\n',
                encoding="utf-8",
            )
            with patch.object(config, "CONFIG_PATH", config_path), patch.object(config, "ROOT_DIR", root), redirect_stdout(io.StringIO()):
                url = "https://example.com/video"
                self.assertEqual(cli.main(["download", url]), 0)
                download.assert_called_with(url, root / "saved", output_format="webm", resolution_height=720)
                ensure_tools.assert_called_with(spotdl=False)

                output_path = root / "explicit"
                self.assertEqual(cli.main(["download", url, "-r", "best", "-f", "mp3", "-o", str(output_path)]), 0)
                download.assert_called_with(url, output_path, output_format="mp3", resolution_height=None)

                self.assertEqual(cli.main(["download", url, "-r", "1080p", "-f", "gif"]), 0)
                download.assert_called_with(url, root / "saved", output_format="gif", resolution_height=1080)

                download.return_value = False
                with redirect_stderr(io.StringIO()):
                    self.assertEqual(cli.main(["download", url]), 1)

    @patch("cli.ensure_tools")
    def test_invalid_download_options_fail_before_setup(self, ensure_tools) -> None:
        for options in (["-r", "bad"], ["-r", "-1"], ["-f", "unknown"]):
            with self.subTest(options=options), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                cli.main(["download", "https://example.com/video", *options])

            self.assertEqual(error.exception.code, 2)

        ensure_tools.assert_not_called()

    @patch("cli.ensure_tools")
    @patch("cli.convert_file")
    def test_convert_defaults_formats_and_output_extension(self, convert_file, ensure_tools) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "音声.mp3"
            source.write_bytes(b"source")
            config_path = root / "config.toml"
            config_path.write_text(
                '[download]\noutput_path = "saved"\ndefault_format = "wav"\n',
                encoding="utf-8",
            )
            with patch.object(config, "CONFIG_PATH", config_path), patch.object(config, "ROOT_DIR", root), redirect_stdout(io.StringIO()):
                cases = (
                    ([], root / "saved" / "音声.wav"),
                    (["-f", ".TTA"], root / "saved" / "音声.tta"),
                    (["-o", str(root / "output.flac")], root / "output.flac"),
                    (["-o", str(root / "output"), "-f", "wv"], root / "output.wv"),
                )
                for options, output_path in cases:
                    with self.subTest(options=options):
                        self.assertEqual(cli.main(["convert", str(source), *options]), 0)
                        convert_file.assert_called_with(source.resolve(), output_path)

            ensure_tools.assert_called_with(ytd=False, spotdl=False)

    @patch("cli.ensure_tools")
    @patch("cli.convert_file")
    def test_convert_refuses_overwrites_and_reports_failure(self, convert_file, ensure_tools) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.mp3"
            target = root / "target.wav"
            source.write_bytes(b"source")
            target.write_bytes(b"target")
            for output_path in (source, target):
                with self.subTest(output_path=output_path), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    cli.main(["convert", str(source), "-o", str(output_path)])

                self.assertEqual(error.exception.code, 2)

            ensure_tools.assert_not_called()
            convert_file.assert_not_called()
            self.assertEqual(source.read_bytes(), b"source")
            self.assertEqual(target.read_bytes(), b"target")

            convert_file.side_effect = subprocess.CalledProcessError(1, ["ffmpeg"])
            with redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main(["convert", str(source), "-o", str(root / "failed.wav")]), 1)

    @patch("utils.convert.subprocess.run")
    def test_conversion_command_preserves_files_and_propagates_errors(self, run) -> None:
        def write_output(command, **kwargs):
            Path(command[-1]).write_bytes(b"converted")

        run.side_effect = write_output
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "音声 sample.mp3"
            output_path = root / "nested" / "音声 sample.tta"
            source.write_bytes(b"source")
            convert.convert_file(source, output_path)
            self.assertTrue(output_path.parent.is_dir())
            command = run.call_args.args[0]
            self.assertEqual(command[0], str(convert.FFMPEG_PATH))
            self.assertIn("-nostdin", command)
            self.assertIn("-n", command)
            self.assertEqual(command[-3:-1], ["-i", str(source)])
            self.assertEqual(Path(command[-1]).name, output_path.name)
            self.assertEqual(output_path.read_bytes(), b"converted")
            self.assertTrue(run.call_args.kwargs["check"])

            run.reset_mock()
            output_path.write_bytes(b"target")
            for target in (source, output_path):
                with self.subTest(target=target), self.assertRaises(FileExistsError):
                    convert.convert_file(source, target)

            with self.assertRaises(FileNotFoundError):
                convert.convert_file(root / "missing.mp3", root / "missing.wav")
            run.assert_not_called()
            self.assertEqual(source.read_bytes(), b"source")
            self.assertEqual(output_path.read_bytes(), b"target")

            run.side_effect = subprocess.CalledProcessError(1, command)
            with self.assertRaises(subprocess.CalledProcessError):
                convert.convert_file(source, root / "failed.wav")

            self.assertFalse((root / "failed.wav").exists())

    @patch("utils.convert.subprocess.run")
    def test_conversion_refuses_sidecar_collisions(self, run) -> None:
        def write_outputs(command, **kwargs):
            output_path = Path(command[-1])
            output_path.write_bytes(b"playlist")
            output_path.with_name("output0.ts").write_bytes(b"segment")

        run.side_effect = write_outputs
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.wav"
            source.write_bytes(b"source")
            sidecar = root / "output0.ts"
            sidecar.write_bytes(b"existing")
            with self.assertRaises(FileExistsError):
                convert.convert_file(source, root / "output.m3u8")

            self.assertEqual(sidecar.read_bytes(), b"existing")
            self.assertFalse((root / "output.m3u8").exists())

    @patch("utils.ytd.get_js_runtime_options", return_value=[])
    @patch("utils.ytd.get_video_formats", return_value=[{"format_id": "video", "acodec": "none"}])
    @patch("utils.ytd.subprocess.run")
    def test_download_formats_use_audio_extraction_and_video_selection(self, run, get_formats, _runtime) -> None:
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir)
            for output_format in ("wav", "webm", "gif"):
                with self.subTest(output_format=output_format):
                    self.assertTrue(ytd.download("https://example.com/video", output_path, output_format, None, 720))
                    command = run.call_args.args[0]
                    if output_format == "wav":
                        self.assertEqual(command[command.index("--audio-format") + 1], "wav")
                        get_formats.assert_not_called()
                    else:
                        self.assertEqual(command[command.index("--recode-video") + 1], output_format)
                        get_formats.assert_called_with("https://example.com/video", 720, None)
                        self.assertEqual(command[command.index("-f") + 1], "video" if output_format == "gif" else "video+ba[ext=m4a]/video+ba/video")

    def test_saving_download_settings_preserves_format(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text('[download]\ndefault_format = "flac"\n', encoding="utf-8")
            with patch.object(config, "CONFIG_PATH", config_path):
                config.save_download('保存先 "音楽"', 1080)
                self.assertEqual(config.get_default_format(), "flac")
                self.assertEqual(config.get_output_path_value(), '保存先 "音楽"')
                self.assertEqual(config.get_default_resolution(), 1080)


if __name__ == "__main__":
    unittest.main()
