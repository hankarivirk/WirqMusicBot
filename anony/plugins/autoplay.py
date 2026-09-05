# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


from pyrogram import filters, types

from anony import app, db, lang
from anony.helpers import admin_check


@app.on_message(filters.command(["autoplay"]) & filters.group & ~app.bl_users)
@lang.language()
@admin_check
async def autoplay_hndlr(_, m: types.Message) -> None:
    if len(m.command) < 2:
        state = await db.get_autoplay(m.chat.id)
        status = m.lang.get("autoplay_enabled", "ON") if state else m.lang.get(
            "autoplay_disabled", "OFF"
        )
        return await m.reply_text(
            m.lang.get(
                "autoplay_status",
                "🔁 Autoplay is currently <b>{0}</b>.\n\nUsage: <code>/autoplay on</code> or <code>/autoplay off</code>",
            ).format(status)
        )

    arg = m.command[1].lower()
    if arg in ("on", "enable", "true", "1"):
        await db.set_autoplay(m.chat.id, True)
        return await m.reply_text(
            m.lang.get(
                "autoplay_on",
                "🔁 Autoplay enabled — when the queue ends, a related track keeps playing automatically.",
            )
        )
    elif arg in ("off", "disable", "false", "0"):
        await db.set_autoplay(m.chat.id, False)
        return await m.reply_text(
            m.lang.get("autoplay_off", "⏹ Autoplay disabled.")
        )

    await m.reply_text(
        m.lang.get(
            "autoplay_usage",
            "Usage: <code>/autoplay on</code> or <code>/autoplay off</code>",
        )
    )
