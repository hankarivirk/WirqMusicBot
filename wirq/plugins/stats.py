# Wirq Music Bot - Analytics & System Stats Plugin (Section 12)
import sys
import psutil
from pyrogram import filters, types
from wirq import app, db, config

def _format_bytes(b: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if b < 1024.0:
            return f"{b:.1f} {unit}"
        b /= 1024.0
    return f"{b:.1f} TB"

@app.on_message(filters.command(["stats"]) & ~app.bl_users)
async def _stats(_, m: types.Message):
    is_owner = (m.from_user.id == app.owner_id) or (m.from_user.id in app.sudoers)
    stats = await db.get_stats()
    
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    if is_owner:
        # Full owner statistics
        text = (
            f"📊 <b>{config.BOT_NAME} Comprehensive Owner Metrics:</b>\\n\\n"
            f"• <b>Total Tracks Streamed:</b> <code>{stats.get('tracks_played', 0):,}</code>\\n"
            f"• <b>Active Streaming Voice Chats:</b> <code>{stats.get('active_calls', 0)}</code>\\n"
            f"• <b>Registered Groups:</b> <code>{len(await db.get_chats()):,}</code>\\n\\n"
            f"<b>🖥️ Server Resources:</b>\\n"
            f"• <b>CPU Utilization:</b> <code>{cpu}%</code>\\n"
            f"• <b>RAM Usage:</b> <code>{ram.percent}%</code> ({_format_bytes(ram.used)} / {_format_bytes(ram.total)})\\n"
            f"• <b>Disk Usage:</b> <code>{disk.percent}%</code> ({_format_bytes(disk.used)} / {_format_bytes(disk.total)})\\n"
            f"• <b>Python Runtime:</b> <code>{sys.version.split()[0]}</code>\\n\\n"
            f"<i>Private Owner Audit Log</i>"
        )
    else:
        # Clean public summary
        text = (
            f"📊 <b>{config.BOT_NAME} Live Stats:</b>\\n\\n"
            f"• <b>Total Tracks Played:</b> <code>{stats.get('tracks_played', 0):,}</code>\\n"
            f"• <b>Active Streaming Groups:</b> <code>{stats.get('active_calls', 0)}</code>\\n"
            f"• <b>System Health:</b> <code>Optimal (CPU {cpu}% | RAM {ram.percent}%)</code>\\n\\n"
            f"<i>Channel: @wirqbots</i>"
        )

    await m.reply_text(
        text,
        reply_markup=types.InlineKeyboardMarkup([
            [types.InlineKeyboardButton("💬 Support Channel", url=config.SUPPORT_CHANNEL)]
        ])
    )
