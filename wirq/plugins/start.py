# Wirq Music Bot - Welcome & Help Plugin
from pyrogram import filters, types
from wirq import app, config, lang
from wirq.helpers import buttons

@app.on_message(filters.command(["start"]) & ~app.bl_users)
@lang.language()
async def _start(_, m: types.Message):
    bot_user = app.username or "WirqMusicBot"
    if m.chat.type.value == "private":
        caption = (
            f"👋 <b>Welcome to {config.BOT_NAME}!</b>\\n\\n"
            f"I am a lightning-fast, high-definition music streaming bot for Telegram voice chats, "
            f"supporting lossless audio, 720p HD video, live Apple Music-styled player cards, "
            f"intelligent autoplay recommendations, multi-tier loop modes, and multi-language support.\\n\\n"
            f"<b>Owner:</b> {config.OWNER_USERNAME}\\n"
            f"<b>Support Channel:</b> @wirqbots\\n\\n"
            f"<i>Tap the buttons below to explore features or add me to your group!</i>"
        )
        markup = buttons.start_markup(bot_username=bot_user)
        try:
            await m.reply_photo(
                photo=config.START_THUMBNAIL_URL,
                caption=caption,
                reply_markup=markup
            )
        except Exception:
            await m.reply_text(caption, reply_markup=markup)
    else:
        await m.reply_text(
            f"✨ <b>{config.BOT_NAME} is online and ready to stream in {m.chat.title}!</b>\\n"
            f"Use <code>/play &lt;song name or link&gt;</code> to begin.",
            reply_markup=types.InlineKeyboardMarkup([
                [types.InlineKeyboardButton("💬 Support Channel", url=config.SUPPORT_CHANNEL)]
            ])
        )

@app.on_message(filters.command(["help"]) & ~app.bl_users)
@lang.language()
async def _help(_, m: types.Message):
    text = (
        f"<b>📚 {config.BOT_NAME} Command Center:</b>\\n\\n"
        "<b>🎵 Playback:</b>\\n"
        "• <code>/play &lt;song/link&gt;</code> - Stream audio in group voice chat\\n"
        "• <code>/vplay &lt;video/link&gt;</code> - Stream video + audio in HD\\n"
        "• <code>/search &lt;query&gt;</code> - Search YouTube with interactive buttons\\n"
        "• <code>/pause</code> - Pause active voice stream\\n"
        "• <code>/resume</code> - Resume paused playback\\n"
        "• <code>/skip</code> - Skip to next song in queue\\n"
        "• <code>/stop</code> - Stop playback and clear voice chat\\n"
        "• <code>/clear</code> - Clear upcoming queue items\\n"
        "• <code>/queue</code> - View playlist queue\\n"
        "• <code>/replay</code> - Replay current song from start\\n"
        "• <code>/seek &lt;seconds&gt;</code> - Jump to specific timestamp\\n"
        "• <code>/shuffle</code> - Randomize remaining tracks\\n"
        "• <code>/leave</code> - Force assistant to leave voice chat\\n\\n"
        "<b>⚙️ Settings & Controls:</b>\\n"
        "• <code>/loop [off|song|queue]</code> - Toggle 3-state loop mode\\n"
        "• <code>/autoplay [on|off]</code> - Toggle continuous smart recommendations\\n"
        "• <code>/volume &lt;1-100&gt;</code> - Adjust stream volume\\n"
        "• <code>/thumbnail [on|off]</code> - Group custom thumbnail card toggle\\n"
        "• <code>/lang</code> or <code>/language</code> - Change bot language (EN/HI/PA)\\n"
        "• <code>/ping</code> - Check latency, uptime and player status\\n"
        "• <code>/stats</code> - Bot usage analytics\\n\\n"
        f"<i>Maintained by {config.OWNER_USERNAME} • Channel: @wirqbots</i>"
    )
    await m.reply_text(text, reply_markup=buttons.help_markup())
