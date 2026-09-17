# Copyright (c) 2025 wirq4
# Licensed under the MIT License.
# Playback Handler for Wirq Music Bot

from urllib.parse import urlsplit, parse_qs
from pyrogram import filters, types
from wirq import anon, app, config, db, lang, queue, tg, yt
from wirq.helpers import Track, buttons, telegraph, utils, checkUB

def _is_playlist_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
    except Exception:
        return False
    if parts.path.rstrip("/").endswith("/playlist"):
        return True
    return "list" in parse_qs(parts.query)

@app.on_message(
    filters.command(["play", "playforce", "vplay", "vplayforce", "playmusic", "playmusicforce"])
    & filters.group
    & ~app.bl_users
)
@lang.language()
@checkUB
async def play_hndlr(_, m: types.Message):
    cmd = m.command[0].lower()
    force = "force" in cmd
    video = "vplay" in cmd
    music = "playmusic" in cmd
    mention = m.from_user.mention
    chat_id = m.chat.id

    sent = await m.reply_text("🔎 <b>Searching...</b>")
    track = None

    # 1. Reply to Telegram Audio/Video File
    if m.reply_to_message and tg.get_media(m.reply_to_message):
        media = m.reply_to_message
        await sent.edit_text("⬇️ <b>Downloading Telegram media...</b>")
        file_path = await tg.download(media, sent)
        if not file_path:
            return await sent.edit_text("❌ Failed to download Telegram media.")
        title = "Telegram Audio"
        if media.audio and media.audio.title:
            title = media.audio.title
        elif media.video and media.video.file_name:
            title = media.video.file_name
        track = Track(
            id=str(media.id),
            title=title[:50],
            duration="00:00",
            duration_sec=0,
            file_path=file_path,
            user=mention,
            video=video,
        )

    # 2. Text Query or URL Provided
    elif len(m.command) >= 2:
        query = " ".join(m.command[1:]).strip()

        # Playlist Link
        if _is_playlist_url(query):
            await sent.edit_text("📋 <b>Fetching YouTube playlist...</b>")
            plist = await yt.playlist(query, limit=config.PLAYLIST_LIMIT)
            if plist:
                first_track = plist[0]
                first_track.user = mention
                queued_count = 0
                for item in plist[1:]:
                    if len(queue.get_queue(chat_id)) < config.QUEUE_LIMIT:
                        item.user = mention
                        queue.add(chat_id, item)
                        queued_count += 1
                track = first_track
                await sent.edit_text(f"📋 <b>Loaded playlist:</b> Queued {queued_count + 1} tracks.")
            else:
                track = await yt.search(query, sent.id, video=video, music=music)
                if not track:
                    return await sent.edit_text("❌ Failed to extract playlist tracks.")
                track.user = mention

        # Direct Video Link or Keyword Search
        else:
            track = await yt.search(query, sent.id, video=video, music=music)
            if not track:
                return await sent.edit_text("❌ <b>No results found.</b> Please check the title or URL.")
            track.user = mention
    else:
        return await sent.edit_text("<b>Usage:</b> <code>/play [song title or YouTube link]</code>")

    # Duration Limit Check
    if track.duration_sec and track.duration_sec > config.DURATION_LIMIT:
        return await sent.edit_text(
            f"⚠️ Track duration exceeds the {config.DURATION_LIMIT // 60} minutes limit."
        )

    # Queue or Force Play
    if force:
        queue.force_play_new(chat_id, track)
    else:
        if len(queue.get_queue(chat_id)) >= config.QUEUE_LIMIT:
            return await sent.edit_text(f"⚠️ Queue is full ({config.QUEUE_LIMIT} tracks limit).")
        pos = queue.add(chat_id, track)
        if pos != 0 or await db.get_call(chat_id):
            track_url = track.url or ""
            track_title = utils.esc(track.title)
            msg_text = (
                f"➕ <b>Queued at #{pos}:</b> <a href='{track_url}'>{track_title}</a>\n"
                f"⏱ <b>Duration:</b> {track.duration}\n"
                f"👤 <b>Requested by:</b> {mention}"
            )
            return await sent.edit_text(
                msg_text,
                reply_markup=buttons.play_queued(chat_id, pos, track.id, "Play Now")
            )

    # Start playback immediately for the first song
    if not track.file_path:
        await sent.edit_text("⬇️ <b>Downloading high-speed audio...</b>")
        track.file_path = await yt.download(track.id, video=video)

    if not track.file_path:
        return await sent.edit_text("❌ Could not download audio stream from YouTube.")

    track.message_id = sent.id
    await anon.play_media(chat_id=chat_id, message=sent, media=track)
