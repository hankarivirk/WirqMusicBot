import asyncio
import importlib
import logging
import shutil
import sys
from pyrogram import idle
from anony.core.bot import Bot
from anony.core.userbot import userbot
from anony.core.calls import MusicCall
from anony.core.dir import check_dirs
from anony.core.lang import load_languages
from anony.core.mongo import load_cache, migrate_coll
from anony.plugins import ALL_PLUGINS
import config

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s"
)
LOGGER = logging.getLogger("MusicFlow")

def preflight_check():
    """Validates runtime environment, dependencies, and configuration."""
    LOGGER.info("[MUSIC FLOW] Performing startup preflight check...")
    
    # 1. Python version check
    if sys.version_info < (3, 10):
        LOGGER.error("MUSIC FLOW requires Python 3.10 or higher.")
        sys.exit(1)

    # 2. FFmpeg check
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        LOGGER.warning("FFmpeg binary not detected in PATH. Audio conversion may fail.")
    else:
        LOGGER.info(f"[MUSIC FLOW] FFmpeg detected at: {ffmpeg_bin}")

    # 3. Required ENV validation
    missing = []
    if not config.API_ID: missing.append("API_ID")
    if not config.API_HASH: missing.append("API_HASH")
    if not config.BOT_TOKEN: missing.append("BOT_TOKEN")
    if not config.OWNER_ID: missing.append("OWNER_ID")
    if not config.MONGO_URL: missing.append("MONGO_URL")
    if not config.SESSION: missing.append("SESSION")

    if missing:
        LOGGER.warning(f"Optional or mock runtime environment active; unconfigured variables: {', '.join(missing)}")

    LOGGER.info("[MUSIC FLOW] Preflight check complete.")

async def init():
    preflight_check()
    check_dirs()
    load_languages()
    await load_cache()
    await migrate_coll()

    LOGGER.info("[MUSIC FLOW] Starting Bot, Assistant & Voice Client...")
    await Bot.start()
    await userbot.start()
    await MusicCall.start()

    loaded_count = 0
    for p in ALL_PLUGINS:
        try:
            importlib.import_module(f"anony.plugins.{p}")
            loaded_count += 1
        except Exception as e:
            LOGGER.error(f"[MUSIC FLOW] Error loading plugin '{p}': {e}", exc_info=True)

    LOGGER.info(f"[MUSIC FLOW] Successfully loaded {loaded_count}/{len(ALL_PLUGINS)} plugins.")
    if MusicCall.is_running:
        LOGGER.info("[MUSIC FLOW] PyTgCalls ready for streaming.")
    else:
        LOGGER.warning("[MUSIC FLOW] Voice system unavailable; playback commands will report clean error.")

    await idle()

    LOGGER.info("[MUSIC FLOW] Initiating graceful shutdown...")
    await Bot.stop()
    await userbot.stop()
    await MusicCall.stop(0)
    LOGGER.info("[MUSIC FLOW] Shutdown complete.")

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(init())
