import asyncio
import time

from ui.ui import NCDLApp
from utils.config import Config
from utils.ytd import YTDUpdater, YTD_PATH, FFMPEG_PATH, FFPROBE_PATH

async def main():
    Config.ensure_config()
    
    if not YTD_PATH.exists():
        YTDUpdater.fetch_ytd()
    if not FFMPEG_PATH.exists() or not FFPROBE_PATH.exists():
        YTDUpdater.fetch_ffmpeg()
    
    result = YTDUpdater.update_ytd()
    if not result:
        print("yt-dlpの更新に失敗しました。")
        
    app = NCDLApp()
    await app.run_async()

if __name__ == "__main__":
    asyncio.run(main())
