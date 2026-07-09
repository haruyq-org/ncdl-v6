import asyncio

from ui.app import NCDLApp
from utils import config
from utils.tools import ensure_tools, update_ytd

async def main():
    config.ensure_config()
    ensure_tools()

    if not update_ytd():
        print("yt-dlpの更新に失敗しました。")

    app = NCDLApp()
    await app.run_async()

if __name__ == "__main__":
    asyncio.run(main())
