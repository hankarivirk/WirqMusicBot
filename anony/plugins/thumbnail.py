from pyrogram import filters, types

from anony import app, config, db, lang
from anony.helpers import admin_check


@app.on_message(
    filters.command(["thumbnail", "thumb"])
    & filters.group
    & ~app.bl_users
)
@lang.language()
@admin_check
async def thumbnail_setting(_, m: types.Message):
    """Enable/disable generated player thumbnails for this group.

    Default is OFF. This is intentionally per-group so busy groups can keep
    playback fast without paying the thumbnail CPU/network cost.
    """
    if not config.THUMB_GEN:
        return await m.reply_text(
            "🖼️ Thumbnail generation is disabled globally by the bot owner."
        )

    if len(m.command) < 2:
        state = await db.get_thumbnail_gen(m.chat.id)
        return await m.reply_text(
            f"🖼️ Generated thumbnails are currently **{'ON' if state else 'OFF'}**.\n"
            "Use `/thumbnail on` or `/thumbnail off`."
        )

    value = m.command[1].lower()
    if value in {"on", "enable", "enabled", "1", "true"}:
        await db.set_thumbnail_gen(m.chat.id, True)
        return await m.reply_text(
            "🖼️ Generated player thumbnails are now **ON** for this group."
        )

    if value in {"off", "disable", "disabled", "0", "false"}:
        await db.set_thumbnail_gen(m.chat.id, False)
        return await m.reply_text(
            "🖼️ Generated player thumbnails are now **OFF** for this group.\n"
            "Playback will skip thumbnail generation for lower latency."
        )

    await m.reply_text("Usage: `/thumbnail on` or `/thumbnail off`")
