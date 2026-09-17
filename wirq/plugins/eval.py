import sys
import io
import traceback
from pyrogram import filters, types
from wirq import app

@app.on_message(filters.command(["eval"]) & app.sudoers)
async def _eval(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text("Provide Python code to evaluate.")
    code = m.text.split(None, 1)[1]
    old_stdout = sys.stdout
    buf = io.StringIO()
    sys.stdout = buf
    try:
        exec(code)
        out = buf.getvalue()
        await m.reply_text(f"<code>{out or 'Success (no output)'}</code>")
    except Exception:
        await m.reply_text(f"<code>{traceback.format_exc()}</code>")
    finally:
        sys.stdout = old_stdout
