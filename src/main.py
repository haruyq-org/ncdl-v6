import asyncio
import sys

from utils import config
from utils.tools import ensure_tools, update_ytd

async def main():
    from ui.app import NCDLApp

    config.ensure_config()
    ensure_tools()

    if not update_ytd():
        print("yt-dlpの更新に失敗しました。")

    app = NCDLApp()
    await app.run_async()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        from cli import main as cli_main

        sys.exit(cli_main())
    else:
        asyncio.run(main())
