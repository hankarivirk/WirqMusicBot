# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


from pyrogram import filters, types

from anony import anon, app, db, lang, queue
from anony.helpers import can_manage_vc

# FFmpeg's `bass` filter gain, in dB. 0 disables it entirely (no -af
# flag added at all, so there's zero overhead on chats that never touch
# this). Capped well short of clipping/distortion territory.
MAX_BASS = 20


@app.on_message(filters.command(["bass", "bassboost"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _bass(_, m: types.Message):
    if len(m.command) < 2:
        current = await db.get_bass(m.chat.id)
        return await m.reply_text(m.lang["bass_status"].format(current, MAX_BASS))

    arg = m.command[1].lower()
    if arg in ("off", "reset", "0"):
        level = 0
    elif arg.lstrip("-").isdigit():
        level = int(arg)
    else:
        return await m.reply_text(m.lang["bass_usage"].format(MAX_BASS))

    if level < 0 or level > MAX_BASS:
        return await m.reply_text(m.lang["bass_range"].format(MAX_BASS))

    await db.set_bass(m.chat.id, level)

    if not await db.get_call(m.chat.id):
        return await m.reply_text(
            m.lang["bass_saved"].format(level) if level else m.lang["bass_reset"]
        )

    media = queue.get_current(m.chat.id)
    if media and media.file_path:
        sent = await m.reply_text(
            m.lang["bass_applying"].format(level) if level else m.lang["bass_reset"]
        )
        # Re-runs play_media on the SAME track from its current position
        # — the only way to make FFmpeg pick up a new -af filter value,
        # since it can't be changed on an already-running stream. Mirrors
        # exactly how /seek restarts playback.
        await anon.play_media(m.chat.id, sent, media, max(media.time, 1))
    else:
        await m.reply_text(
            m.lang["bass_saved"].format(level) if level else m.lang["bass_reset"]
        )
