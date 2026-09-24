from pyrogram import filters
from pyrogram.types import Message
from anony import app
from anony.core.calls import MusicCall
from anony.helpers._inline import queue_markup, empty_queue_markup
from anony.helpers._queue import Queues

@app.on_message(filters.command(["queue"]) & filters.group)
async def queue_command(_, message: Message):
    chat_id = message.chat.id
    queue = Queues.get_queue(chat_id)
    curr = MusicCall.active_tracks.get(chat_id)

    if not curr and not queue:
        return await message.reply_text(
            "Queue is clear.\n\nAdd a song to get things moving.",
            reply_markup=empty_queue_markup()
        )

    curr_title = curr.get("title", "Unknown") if curr else "None"
    curr_artist = (curr.get("channel") or curr.get("channel_name") or "") if curr else ""
    curr_line = f"{curr_title} — {curr_artist}" if curr_artist else curr_title

    lines = ["Queue", "", "Current:", "Now playing", curr_line]

    if queue:
        lines.extend(["", "Up next"])
        for idx, t in enumerate(queue[:3], start=1):
            t_title = t.get("title", "Unknown")
            t_artist = t.get("channel") or t.get("channel_name") or ""
            t_line = f"{t_title} — {t_artist}" if t_artist else t_title
            lines.append(f"{idx:02d} {t_line}")
        if len(queue) > 3:
            lines.append(f"{len(queue) - 3} more")

    await message.reply_text("\n".join(lines), reply_markup=queue_markup(chat_id))

@app.on_message(filters.command(["clear"]) & filters.group)
async def clear_command(_, message: Message):
    chat_id = message.chat.id
    Queues.clear_queue(chat_id)
    await message.reply_text("Queue cleared.\n\nPlayback is unchanged.")
