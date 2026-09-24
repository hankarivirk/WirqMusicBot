import logging
import time
from pyrogram import filters
from pyrogram.types import CallbackQuery
from anony import app
import config
from anony.core.calls import MusicCall, REC_SESSIONS
from anony.core.youtube import YouTube
from anony.helpers._admins import is_admin
from anony.helpers._inline import (
    stream_markup,
    recommendation_markup,
    settings_markup,
    autoplay_setting_markup,
    thumbnail_setting_markup,
    global_thumbnail_markup,
    help_main_markup,
    help_category_markup,
    queue_markup,
    empty_queue_markup,
    language_markup,
)
from anony.helpers._queue import Queues
from anony.utils.database import (
    is_autoplay,
    set_autoplay,
    get_thumbnail_setting,
    set_thumbnail_setting,
    get_global_thumbnail_setting,
    set_global_thumbnail_setting,
    get_lang,
    set_lang,
)

LOGGER = logging.getLogger("MusicFlow.Callbacks")

# -------------------------------------------------------------
# 1. PLAYER CONTROLS (▷ II ⥁ ‣‣I ▢, QUEUE, CLOSE)
# -------------------------------------------------------------
@app.on_callback_query(filters.regex(r"^panel_"))
async def player_controls_callback(client, query: CallbackQuery):
    data = query.data.split("_")
    action = data[1]

    if action == "close":
        return await query.message.delete()

    chat_id = int(data[2])

    if not await is_admin(query):
        return await query.answer("I need administrator access to control playback here.", show_alert=True)

    if chat_id not in MusicCall.active_tracks and action not in ["close", "queue"]:
        return await query.answer("Playback couldn't be started.", show_alert=True)

    user_mention = query.from_user.mention if query.from_user else "User"

    if action == "pause":
        success = await MusicCall.pause(chat_id)
        if success:
            await query.answer()
            await query.message.reply_text("Playback paused.")
        else:
            await query.answer("Playback paused.", show_alert=True)

    elif action == "resume":
        success = await MusicCall.resume(chat_id)
        if success:
            await query.answer()
            await query.message.reply_text("Playback resumed.")
        else:
            await query.answer("Playback resumed.", show_alert=True)

    elif action == "replay":
        track = MusicCall.active_tracks.get(chat_id)
        if track:
            success = await MusicCall.play(chat_id, track)
            if success:
                await query.answer()
                await query.message.reply_text("Starting playback...")
            else:
                await query.answer("Playback couldn't be started.", show_alert=True)
        else:
            await query.answer("Nothing is waiting in the queue.", show_alert=True)

    elif action == "skip":
        queue = Queues.get_queue(chat_id)
        await query.answer()
        if queue:
            await query.message.reply_text("Skipped.\n\nStarting the next track.")
        else:
            await query.message.reply_text("Skipped.\n\nNothing is waiting in the queue.")
        await MusicCall.on_song_end(chat_id)

    elif action == "stop":
        await MusicCall.stop(chat_id)
        await query.answer()
        await query.message.reply_text("Playback stopped.\n\nQueue cleared.")

    elif action == "queue":
        q = Queues.get_queue(chat_id)
        current = MusicCall.active_tracks.get(chat_id)
        if not q and not current:
            await query.answer()
            return await query.message.reply_text(
                "Queue is clear.\n\nAdd a song to get things moving.",
                reply_markup=empty_queue_markup()
            )

        curr_title = current.get("title", "Unknown") if current else "None"
        curr_artist = (current.get("channel") or current.get("channel_name") or "") if current else ""
        curr_line = f"{curr_title} — {curr_artist}" if curr_artist else curr_title

        lines = ["Queue", "", "Current:", "Now playing", curr_line]
        if q:
            lines.extend(["", "Up next"])
            for idx, t in enumerate(q[:3], start=1):
                t_title = t.get("title", "Unknown")
                t_artist = t.get("channel") or t.get("channel_name") or ""
                t_line = f"{t_title} — {t_artist}" if t_artist else t_title
                lines.append(f"{idx:02d} {t_line}")
            if len(q) > 3:
                lines.append(f"{len(q) - 3} more")

        await query.answer()
        await query.message.reply_text("\n".join(lines), reply_markup=queue_markup(chat_id))

    elif action == "controls":
        await query.answer()
        await query.message.edit_reply_markup(reply_markup=stream_markup(chat_id))

# -------------------------------------------------------------
# 2. QUEUE BUTTONS
# -------------------------------------------------------------
@app.on_callback_query(filters.regex(r"^queue_clear_"))
async def queue_clear_callback(client, query: CallbackQuery):
    chat_id = int(query.data.split("_")[2])
    if not await is_admin(query):
        return await query.answer("I need administrator access to control playback here.", show_alert=True)
    Queues.clear_queue(chat_id)
    await query.answer()
    await query.message.reply_text("Queue cleared.\n\nPlayback is unchanged.")

@app.on_callback_query(filters.regex(r"^btn_queue$"))
async def dm_queue_callback(client, query: CallbackQuery):
    chat_id = query.message.chat.id
    q = Queues.get_queue(chat_id)
    current = MusicCall.active_tracks.get(chat_id)
    if not q and not current:
        await query.answer()
        return await query.message.reply_text(
            "Queue is clear.\n\nAdd a song to get things moving.",
            reply_markup=empty_queue_markup()
        )
    await query.answer()

# -------------------------------------------------------------
# 3. FORCE PLAY CONTROLS
# -------------------------------------------------------------
@app.on_callback_query(filters.regex(r"^force_play_"))
async def force_play_callback(client, query: CallbackQuery):
    if not await is_admin(query):
        return await query.answer("I need administrator access to control playback here.", show_alert=True)

    parts = query.data.split("_", 2)
    if len(parts) < 3:
        return await query.answer("This button has expired.\n\nOpen the menu again.", show_alert=True)
    vid_id = parts[2]
    chat_id = query.message.chat.id
    await query.answer("Starting playback...")

    track = await YouTube.get_video_metadata(vid_id)
    if not track:
        return await query.message.reply_text("Nothing found.\n\nTry another search.")

    track["requester"] = query.from_user.mention if query.from_user else "User"
    artist = track.get("channel") or track.get("channel_name") or "YouTube"
    dur = track.get("duration") or "Unknown"

    success = await MusicCall.play(chat_id, track)
    if success:
        now_text = (
            "Now playing\n\n"
            f"{track['title']}\n"
            f"{artist}\n\n"
            f"Requested by {track['requester']}\n"
            f"Duration: {dur}"
        )
        await query.message.reply_text(now_text, reply_markup=stream_markup(chat_id))
    else:
        await query.message.reply_text("That track couldn't be played right now.\n\nTry another track or search for the same song again.")

# -------------------------------------------------------------
# 4. SECURE RECOMMENDATION SESSIONS (SECTIONS 20, 53)
# -------------------------------------------------------------
@app.on_callback_query(filters.regex(r"^rec_"))
async def recommendation_callback(client, query: CallbackQuery):
    parts = query.data.split("_", 3)
    if len(parts) < 3:
        return await query.answer("This button has expired.\n\nOpen the menu again.", show_alert=True)
    action = parts[1]
    chat_id = query.message.chat.id

    if action == "play":
        if len(parts) < 4:
            return await query.answer("This button has expired.\n\nOpen the menu again.", show_alert=True)
        session_id = parts[2]
        vid_id = parts[3]

        session = REC_SESSIONS.get(session_id)
        if not session or session.chat_id != chat_id or session.is_expired():
            return await query.answer("This button has expired.\n\nOpen the menu again.", show_alert=True)

        valid_ids = [r.get("video_id") or r.get("id") for r in session.recs]
        if vid_id not in valid_ids:
            return await query.answer("This button has expired.\n\nOpen the menu again.", show_alert=True)

        target_track = next((r for r in session.recs if (r.get("video_id") or r.get("id")) == vid_id), None)
        if not target_track:
            target_track = await YouTube.get_video_metadata(vid_id)

        if not target_track:
            return await query.answer("Nothing found.\n\nTry another search.", show_alert=True)

        target_track["requester"] = query.from_user.mention if query.from_user else "User"
        artist = target_track.get("channel") or target_track.get("channel_name") or "YouTube"
        dur = target_track.get("duration") or "Unknown"

        await query.answer("Starting playback...")

        if not MusicCall.active_tracks.get(chat_id):
            success = await MusicCall.play(chat_id, target_track)
            if success:
                try:
                    await query.message.delete()
                except Exception:
                    pass
                now_text = (
                    "Now playing\n\n"
                    f"{target_track['title']}\n"
                    f"{artist}\n\n"
                    f"Requested by {target_track['requester']}\n"
                    f"Duration: {dur}"
                )
                await query.message.reply_text(now_text, reply_markup=stream_markup(chat_id))
            else:
                await query.message.reply_text("That track couldn't be played right now.\n\nTry another track or search for the same song again.")
        else:
            Queues.add_to_queue(chat_id, target_track)
            queued_text = (
                "Added to queue.\n\n"
                f"{target_track['title']}\n"
                f"{artist}"
            )
            await query.message.reply_text(queued_text)

    elif action == "more":
        if len(parts) < 3:
            return await query.answer("This button has expired.\n\nOpen the menu again.", show_alert=True)
        session_id = parts[2]
        session = REC_SESSIONS.get(session_id)
        if not session or session.chat_id != chat_id or session.is_expired():
            return await query.answer("This button has expired.\n\nOpen the menu again.", show_alert=True)

        new_offset = session.offset + 3
        if new_offset >= len(session.recs):
            fresh = await YouTube.get_recommendations(session.base_vid, limit=12)
            if fresh:
                session.recs = fresh
                new_offset = 0
            else:
                return await query.answer("No recommendations right now.", show_alert=True)

        session.offset = new_offset
        session.expires_at = time.time() + 600
        markup = recommendation_markup(session.recs, session_id, offset=new_offset)
        await query.answer()
        try:
            await query.message.edit_reply_markup(reply_markup=markup)
        except Exception:
            pass

# -------------------------------------------------------------
# 5. SETTINGS CALLBACKS (SECTIONS 35, 36, 37, 38)
# -------------------------------------------------------------
@app.on_callback_query(filters.regex(r"^btn_settings"))
async def open_settings_callback(client, query: CallbackQuery):
    chat_id = query.message.chat.id
    if query.message.chat.type != "private" and not await is_admin(query):
        return await query.answer("I need administrator access to control playback here.", show_alert=True)
    await query.answer()
    await query.message.edit_text("Settings", reply_markup=settings_markup(chat_id))

@app.on_callback_query(filters.regex(r"^set_autoplay_menu_"))
async def autoplay_menu_callback(client, query: CallbackQuery):
    chat_id = int(query.data.split("_")[3])
    if not await is_admin(query):
        return await query.answer("I need administrator access to control playback here.", show_alert=True)
    is_ap = await is_autoplay(chat_id)
    state = "Enabled" if is_ap else "Disabled"
    await query.answer()
    await query.message.edit_text(f"Autoplay\n\n{state}", reply_markup=autoplay_setting_markup(chat_id, is_ap))

@app.on_callback_query(filters.regex(r"^set_ap_"))
async def toggle_ap_callback(client, query: CallbackQuery):
    parts = query.data.split("_")
    action = parts[2]
    chat_id = int(parts[3])
    if not await is_admin(query):
        return await query.answer("I need administrator access to control playback here.", show_alert=True)
    new_state = (action == "on")
    await set_autoplay(chat_id, new_state)
    state = "Enabled" if new_state else "Disabled"
    await query.answer("Updated.")
    await query.message.edit_text(f"Autoplay\n\n{state}", reply_markup=autoplay_setting_markup(chat_id, new_state))

@app.on_callback_query(filters.regex(r"^set_thumb_menu_"))
async def thumb_menu_callback(client, query: CallbackQuery):
    chat_id = int(query.data.split("_")[3])
    if not await is_admin(query):
        return await query.answer("I need administrator access to control playback here.", show_alert=True)
    is_tb = await get_thumbnail_setting(chat_id)
    state = "Enabled" if is_tb else "Disabled"
    await query.answer()
    await query.message.edit_text(f"Thumbnails\n\n{state}", reply_markup=thumbnail_setting_markup(chat_id, is_tb))

@app.on_callback_query(filters.regex(r"^set_tb_"))
async def toggle_tb_callback(client, query: CallbackQuery):
    parts = query.data.split("_")
    action = parts[2]
    chat_id = int(parts[3])
    if not await is_admin(query):
        return await query.answer("I need administrator access to control playback here.", show_alert=True)
    new_state = (action == "on")
    await set_thumbnail_setting(chat_id, new_state)
    state = "Enabled" if new_state else "Disabled"
    await query.answer("Updated.")
    await query.message.edit_text(f"Thumbnails\n\n{state}", reply_markup=thumbnail_setting_markup(chat_id, new_state))

@app.on_callback_query(filters.regex(r"^(set_lang_|settings_lang)"))
async def lang_menu_callback(client, query: CallbackQuery):
    chat_id = query.message.chat.id
    if query.message.chat.type != "private" and not await is_admin(query):
        return await query.answer("I need administrator access to control playback here.", show_alert=True)
    await query.answer()
    await query.message.edit_text("Language\n\nChoose your language.", reply_markup=language_markup(chat_id))

@app.on_callback_query(filters.regex(r"^lang_"))
async def select_lang_callback(client, query: CallbackQuery):
    parts = query.data.split("_")
    lang_code = parts[1]
    chat_id = int(parts[2]) if len(parts) > 2 else query.message.chat.id
    if query.message.chat.type != "private" and not await is_admin(query):
        return await query.answer("I need administrator access to control playback here.", show_alert=True)
    await set_lang(chat_id, lang_code)
    await query.answer("Language updated.", show_alert=True)
    try:
        await query.message.delete()
    except Exception:
        pass

@app.on_callback_query(filters.regex(r"^settings_close$"))
async def settings_close_callback(_, query: CallbackQuery):
    await query.message.delete()

# -------------------------------------------------------------
# 6. OWNER GLOBAL THUMBNAIL MASTER CONTROL
# -------------------------------------------------------------
@app.on_callback_query(filters.regex(r"^owner_gthumb_"))
async def owner_gthumb_callback(_, query: CallbackQuery):
    if query.from_user.id != config.OWNER_ID:
        return await query.answer("This action isn't available to you.", show_alert=True)

    action = query.data.split("_")[2]
    if action == "close":
        return await query.message.delete()

    new_state = (action == "on")
    await set_global_thumbnail_setting(new_state)
    state_str = "Enabled" if new_state else "Disabled"
    await query.answer("Updated.")
    await query.message.edit_text(f"Thumbnails\n\n{state_str}", reply_markup=global_thumbnail_markup(new_state))

# -------------------------------------------------------------
# 7. HELP NAVIGATION CALLBACKS (SECTIONS 41, 42)
# -------------------------------------------------------------
HELP_TEXTS = {
    "playback": (
        "Playback\n\n"
        "/play — play a track\n"
        "/vplay — play in voice chat\n"
        "/pause — pause playback\n"
        "/resume — resume playback\n"
        "/skip — skip the current track\n"
        "/stop — stop playback\n"
        "/seek — jump to a position"
    ),
    "queue": (
        "Queue\n\n"
        "/queue — view the queue\n"
        "/clear — clear the queue"
    ),
    "discovery": (
        "Discovery\n\n"
        "/search — search for music\n"
        "/recommend — get recommendations"
    ),
    "settings": (
        "Settings\n\n"
        "/settings — manage playback settings\n"
        "/autoplay — control autoplay"
    ),
}

@app.on_callback_query(filters.regex(r"^help_"))
async def help_navigation_callback(_, query: CallbackQuery):
    cat = query.data.split("_")[1]
    if cat == "close":
        return await query.message.delete()
    elif cat == "main":
        await query.answer()
        return await query.message.edit_text(
            "Help\n\n"
            "Everything you need, without the noise.",
            reply_markup=help_main_markup()
        )
    elif cat in HELP_TEXTS:
        await query.answer()
        return await query.message.edit_text(
            HELP_TEXTS[cat],
            reply_markup=help_category_markup()
        )
