# Wirq Music Bot - Ping & Diagnostic Plugin (Section 11)
import time
import psutil
from pyrogram import filters, types
from wirq import app, calls, config, boot

def _format_uptime(seconds: int) -> str:
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if days > 0: parts.append(f"{days}d")
    if hours > 0: parts.append(f"{hours}h")
    if minutes > 0: parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)

@app.on_message(filters.command(["ping"]) & ~app.bl_users)
async def _ping(_, m: types.Message):
    start = time.time()
    sent = await m.reply_text("🏓 <b>Pinging server and streaming engine...</b>")
    end = time.time()

    latency = round((end - start) * 1000, 1)
    uptime_sec = int(time.time() - boot)
    uptime_str = _format_uptime(uptime_sec)

    # Measure voice chat client latency and readiness
    vc_ping = await calls.ping()
    player_ready = bool(calls.clients)
    status_emoji = "🟢 READY" if player_ready else "🔴 ASSISTANT OFFLINE"

    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent

    caption = (
        f"🏓 <b>Pong! System Diagnostics:</b>\\n\\n"
        f"• <b>Telegram Round-trip Latency:</b> <code>{latency} ms</code>\\n"
        f"• <b>Voice-Chat Stream Latency:</b> <code>{vc_ping} ms</code>\\n"
        f"• <b>Player Engine Status:</b> <code>{status_emoji}</code>\\n"
        f"• <b>Bot Uptime:</b> <code>{uptime_str}</code>\\n"
        f"• <b>CPU Load:</b> <code>{cpu}%</code> | <b>RAM Usage:</b> <code>{ram}%</code>\\n\\n"
        f"<i>{config.BOT_NAME} • @wirqbots</i>"
    )

    try:
        await sent.delete()
        await m.reply_photo(
            photo=config.PING_THUMBNAIL_URL,
            caption=caption,
            reply_markup=types.InlineKeyboardMarkup([
                [types.InlineKeyboardButton("💬 Support Channel", url=config.SUPPORT_CHANNEL)]
            ])
        )
    except Exception:
        await sent.edit_text(caption)
