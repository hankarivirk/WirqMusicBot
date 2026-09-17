# Wirq Music Bot - Thumbnail Settings Plugin (Section 6)
from pyrogram import filters, types
from wirq import app, db, lang, config
from wirq.helpers import can_manage_vc

@app.on_message(filters.command(["thumbnail"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _thumbnail(_, m: types.Message):
    grp_pref = await db.get_thumbnail_pref(m.chat.id)
    glob_pref = await db.get_global_thumbnail()
    env_pref = config.THUMB_GEN
    effective = await db.is_thumb_enabled(m.chat.id)

    if len(m.command) < 2:
        return await m.reply_text(
            f"🖼️ <b>Player Card / Thumbnail Status:</b>\\n\\n"
            f"• <b>Group Setting:</b> <code>{grp_pref if grp_pref is not None else 'Default (Not Set)'}</code>\\n"
            f"• <b>Global Default:</b> <code>{glob_pref if glob_pref is not None else 'Default (Not Set)'}</code>\\n"
            f"• <b>ENV Value:</b> <code>{env_pref}</code>\\n"
            f"• <b>Effective State:</b> <code>{'ENABLED' if effective else 'DISABLED'}</code>\\n\\n"
            f"<i>Priority Order: Group Setting &gt; Global Default &gt; ENV Value</i>\\n\\n"
            f"To toggle: <code>/thumbnail on</code> or <code>/thumbnail off</code>"
        )

    arg = m.command[1].lower()
    if arg in ["on", "enable", "true", "1"]:
        await db.set_thumbnail_pref(m.chat.id, True)
        await m.reply_text("🖼️ <b>Custom Apple Music-style player cards enabled for this group.</b>")
    elif arg in ["off", "disable", "false", "0"]:
        await db.set_thumbnail_pref(m.chat.id, False)
        await m.reply_text("🖼️ <b>Player cards disabled for this group (text mode active).</b>")
    elif arg in ["reset", "default"]:
        await db.set_thumbnail_pref(m.chat.id, None)
        await m.reply_text("🖼️ <b>Group thumbnail setting reset to inherit global default.</b>")
    else:
        await m.reply_text("<b>Usage:</b> <code>/thumbnail [on|off|reset]</code>")

@app.on_message(filters.command(["setthumbnail"]) & ~app.bl_users)
async def _setthumbnail(_, m: types.Message):
    if m.from_user.id != app.owner_id and m.from_user.id not in app.sudoers:
        return await m.reply_text("❌ This command is restricted to the bot owner.")

    if len(m.command) < 2:
        glob = await db.get_global_thumbnail()
        return await m.reply_text(
            f"👑 <b>Owner Global Thumbnail Setting:</b> <code>{glob}</code>\\n\\n"
            f"Usage: <code>/setthumbnail [on|off]</code>"
        )

    arg = m.command[1].lower()
    if arg in ["on", "enable", "true", "1"]:
        await db.set_global_thumbnail(True)
        await m.reply_text("👑 <b>Global default thumbnail cards enabled bot-wide.</b>")
    elif arg in ["off", "disable", "false", "0"]:
        await db.set_global_thumbnail(False)
        await m.reply_text("👑 <b>Global default thumbnail cards disabled bot-wide.</b>")
    else:
        await m.reply_text("<b>Usage:</b> <code>/setthumbnail [on|off]</code>")
