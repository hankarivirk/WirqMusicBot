# Wirq Music Bot - Main Application Entrypoint
# Bot Name: Wirq Music Bot
# Owner: @wirq4 | Support: @wirqbots | GitHub: Hankarivirk/WirqMusicbot

import os
import asyncio
import importlib
from pyrogram import idle
from aiohttp import web

from wirq import (
    app,
    userbot,
    calls,
    db,
    yt,
    config,
    logger,
)
from wirq.core.cleanup import cleanup_worker
from wirq.plugins import all_modules

async def start_health_server():
    port = os.getenv("PORT")
    if not port:
        return
    health_app = web.Application()
    async def health_handler(request):
        return web.Response(text="WirqMusic Bot is running! OK 200")
    health_app.router.add_get("/", health_handler)
    health_app.router.add_get("/health", health_handler)
    runner = web.AppRunner(health_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(port))
    await site.start()
    logger.info(f"Healthcheck HTTP server active on port {port}")

async def boot():
    config.check()
    await db.connect()

    if config.COOKIES_URL:
        await yt.save_cookies(config.COOKIES_URL)

    await app.boot()
    await userbot.boot()
    await calls.boot()

    # Launch background periodic cleanup daemon (Section 13)
    asyncio.create_task(cleanup_worker())

    # Load all plugin modules
    for module in all_modules:
        importlib.import_module(f"wirq.plugins.{module}")
    logger.info(f"Loaded {len(all_modules)} feature modules successfully.")

    await start_health_server()
    logger.info(f"{config.BOT_NAME} startup sequence completed successfully!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(boot())
    except (KeyboardInterrupt, SystemExit):
        pass
