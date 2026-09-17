import asyncio
from pyrogram import filters, types
from wirq import anon, app, config, db, logger

@app.on_message(filters.video_chat_ended)
async def _vc_ended(_, m: types.Message):
    await anon.stop(m.chat.id)

async def auto_leave_worker():
    while config.AUTO_LEAVE:
        await asyncio.sleep(config.CLEANUP_INTERVAL)
        try:
            for cid in list(db.active_calls.keys()):
                if not await db.playing(cid):
                    await anon.stop(cid)
        except Exception as e:
            logger.warning(f"Auto-leave worker error: {e}")
