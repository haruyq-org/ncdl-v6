import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx

from utils import config, ytd
from utils.convert import convert_file
from utils.tools import ensure_tools


def parse_resolution(value: str) -> int | None:
    value = value.lower()
    if value == "best":
        return None

    value = value.removesuffix("p")
    if not value.isdecimal() or int(value) <= 0:
        raise argparse.ArgumentTypeError("画質は正の整数（例: 1080、1080p）またはbestで指定してください。")

    return int(value)


def parse_format(value: str) -> str:
    value = value.lower().removeprefix(".")
    if re.fullmatch(r"[a-z0-9][a-z0-9_-]*", value) is None:
        raise argparse.ArgumentTypeError("形式は拡張子（例: mp4、wav）で指定してください。")

    return value


def parse_url(value: str) -> str:
    parsed_url = urlparse(value)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        raise argparse.ArgumentTypeError("httpまたはhttpsの動画URLを指定してください。")

    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="動画のダウンロードとファイルの変換")
    commands = parser.add_subparsers(dest="command", required=True)

    download = commands.add_parser("download", help="動画・音声をダウンロード")
    download.add_argument("url", type=parse_url, help="動画のURL")
    download.add_argument(
        "-r", "--resolution", type=parse_resolution, default=argparse.SUPPRESS,
        help="動画の画質（例: 1080p、best）。省略時はconfigのdefault_resolution",
    )
    download.add_argument(
        "-f", "--format", type=parse_format, choices=ytd.DOWNLOAD_FORMATS,
        help="出力形式。省略時はconfigのdefault_format",
    )
    download.add_argument("-o", "--output", type=Path, help="保存先フォルダ。省略時はconfigのoutput_path")

    convert = commands.add_parser("convert", help="ローカルファイルを変換")
    convert.add_argument("input", type=Path, help="変換するファイル")
    convert.add_argument(
        "-f", "--format", type=parse_format,
        help="出力拡張子（例: wav、flac、webm）。省略時は出力ファイルの拡張子、なければconfigのdefault_format",
    )
    convert.add_argument("-o", "--output", type=Path, help="出力ファイル。省略時はconfigのoutput_pathに保存")

    args = parser.parse_args(argv)

    try:
        if args.command == "download":
            output_format = args.format or parse_format(config.get_default_format())
            if output_format not in ytd.DOWNLOAD_FORMATS:
                parser.error(f"default_formatが未対応の形式です: {output_format}。download --helpで形式を確認してください。")

            resolution_height = args.resolution if hasattr(args, "resolution") else config.get_default_resolution()
            if resolution_height is not None and resolution_height <= 0:
                parser.error("configのdefault_resolutionは正の整数またはbestにしてください。")

            output_path = args.output.expanduser() if args.output is not None else config.get_output_path()
            ensure_tools(spotdl=False)
            if not ytd.download(
                args.url,
                output_path,
                output_format=output_format,
                resolution_height=resolution_height,
            ):
                print(f"ダウンロードに失敗しました: {args.url}。URLと出力形式を確認してください。", file=sys.stderr)
                return 1
        else:
            input_path = args.input.expanduser().resolve()
            if not input_path.is_file():
                parser.error(f"変換元ファイルが見つかりません: {input_path}")

            output_path = args.output.expanduser() if args.output is not None else None
            suffix = output_path.suffix if output_path is not None else ""
            output_format = args.format or parse_format(suffix or config.get_default_format())
            if suffix and parse_format(suffix) != output_format:
                parser.error("出力ファイルの拡張子と--formatを一致させてください。")

            if output_path is None:
                output_path = config.get_output_path() / input_path.with_suffix(f".{output_format}").name
            elif not suffix:
                output_path = output_path.with_suffix(f".{output_format}")

            if output_path.exists() or output_path.is_symlink():
                parser.error(f"出力先は既に存在します: {output_path}。別のファイル名を指定してください。")

            ensure_tools(ytd=False, spotdl=False)
            convert_file(input_path, output_path)

        print(f"保存先: {output_path.resolve()}")
        return 0
    except (OSError, ValueError, RuntimeError, argparse.ArgumentTypeError, httpx.HTTPError, subprocess.CalledProcessError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("処理を中断しました。", file=sys.stderr)
        return 130
