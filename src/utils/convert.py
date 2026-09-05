import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from utils.tools import FFMPEG_PATH


def convert_file(input_path: Path, output_path: Path) -> None:
    input_path = input_path.expanduser().absolute()
    output_path = output_path.expanduser().absolute()

    if not input_path.is_file():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {input_path}")
    if output_path.exists() or output_path.is_symlink():
        raise FileExistsError(f"出力先が既に存在します。別のパスを指定してください: {output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    # FFmpegの-nは連番画像やHLSの分割ファイルを保護しない。
    with TemporaryDirectory(dir=output_path.parent) as temp_dir:
        temp_path = Path(temp_dir)
        subprocess.run(
            [
                str(FFMPEG_PATH),
                "-hide_banner",
                "-nostdin",
                "-n",
                "-i",
                str(input_path),
                str(temp_path / output_path.name),
            ],
            check=True,
        )
        files = [path for path in temp_path.rglob("*") if path.is_file()]
        for path in files:
            target = output_path.parent / path.relative_to(temp_path)
            if target.exists() or target.is_symlink():
                raise FileExistsError(f"出力先が既に存在します。別のパスを指定してください: {target}")

        for path in files:
            target = output_path.parent / path.relative_to(temp_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            with path.open("rb") as source, target.open("xb") as destination:
                shutil.copyfileobj(source, destination)
