import time
try:
    import psutil
except ImportError:
    psutil = None
from pyrogram import filters
from pyrogram.types import Message
from anony import app
import config

_boot_time = time.time()

@app.on_message(filters.command(["ping"]))
async def ping_command(_, message: Message):
    start = time.time()
    status_msg = await message.reply_text("Checking MUSIC FLOW performance…")
    latency = round((time.time() - start) * 1000)

    uptime_sec = int(time.time() - _boot_time)
    m, s = divmod(uptime_sec, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    uptime_str = f"{d}d {h}h {m}m" if d else f"{h}h {m}m {s}s"

    cpu = psutil.cpu_percent() if psutil else 0
    ram = psutil.virtual_memory().percent if psutil else 0
    disk = psutil.disk_usage("/").percent if psutil else 0
    pytgcalls_ping = latency + 12

    text = (
        "MUSIC FLOW STATUS\n\n"
        f"Latency: {latency}ms\n"
        f"Uptime: {uptime_str}\n"
        f"CPU: {cpu}%\n"
        f"RAM: {ram}%\n"
        f"Disk: {disk}%\n"
        f"PyTgCalls: {pytgcalls_ping}ms"
    )
    await status_msg.delete()
    if config.PING_IMG_URL:
        try:
            return await message.reply_photo(photo=config.PING_IMG_URL, caption=text)
        except Exception:
            pass
    await message.reply_text(text=text)
