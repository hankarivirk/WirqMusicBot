from pyrogram import filters
from pyrogram.types import Message
from anony import app
from anony.helpers._exec import execute_code
from anony.utils.database import is_sudo
import config

@app.on_message(filters.command(["eval", "sh"]))
async def eval_cmd(_, message: Message):
    if not await is_sudo(message.from_user.id):
        return
    if len(message.command) < 2:
        return await message.reply_text("Please provide python code to execute.")
    
    code = message.text.split(None, 1)[1]
    scope = {"app": app, "message": message, "config": config}
    result = await execute_code(code, scope)
    if len(result) > 4096:
        result = result[:4090] + "..."
    await message.reply_text(f"```python\n{result}\n```")
