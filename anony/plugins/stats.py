import sys
import platform
try:
    import psutil
except ImportError:
    psutil = None
from pyrogram import filters
try:
    from pyrogram import __version__ as pyro_version
except ImportError:
    pyro_version = "2.0.106"
from pyrogram.types import Message
try:
    from pytgcalls import __version__ as pytg_version
except ImportError:
    pytg_version = "0.9.7"
from anony import app
from anony.utils.database import is_sudo, get_sudoers

@app.on_message(filters.command(["stats"]))
async def stats_command(_, message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if await is_sudo(user_id):
        ram = f"{psutil.virtual_memory().percent}%" if psutil else "0%"
        cpu = f"{psutil.cpu_percent()}%" if psutil else "0%"
        storage = f"{psutil.disk_usage('/').percent}%" if psutil else "0%"
        py_ver = sys.version.split()[0]
        os_platform = platform.system()

        text = (
            "MUSIC FLOW SYSTEM\n\n"
            "Modules: 28\n"
            f"Platform: {os_platform}\n"
            f"RAM: {ram}\n"
            f"CPU: {cpu}\n"
            f"Storage: {storage}\n"
            f"Python: {py_ver}\n"
            f"Pyrogram: {pyro_version}\n"
            f"PyTgCalls: {pytg_version}"
        )
    else:
        user_name = message.from_user.first_name if message.from_user else "User"
        sudo_list = await get_sudoers()
        text = (
            f"{user_name} STATUS\n\n"
            "Assistants: 1\n"
            "Auto leave: True\n"
            "Blocked chats: 0\n"
            "Blocked users: 0\n"
            f"Sudo users: {len(sudo_list)}\n"
            "Served chats: 1\n"
            "Served users: 1"
        )
    await message.reply_text(text=text)
