# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


from urllib.parse import urlsplit, parse_qs

from pyrogram import filters, types

from anony import anon, app, config, db, lang, logger, queue, tg, yt
from anony.helpers import Track, buttons, telegraph, utils
from anony.helpers._play import checkUB

# Playlists larger than this get a Telegra.ph page instead of an in-chat
# list, since Telegram messages (and the old truncated blockquote) can't
# comfortably fit a long tracklist.
PLAYLIST_WEB_THRESHOLD = 20


def _is_playlist_url(url: str) -> bool:
    """Detect an actual YouTube playlist link (a `list=` query param, or a
    /playlist path) instead of a bare substring check that would false
    -positive on any URL that happens to contain the word "playlist"."""
    try:
        parts = urlsplit(url)
    except Exception:
        return False
    if parts.path.rstrip("/").endswith("/playlist"):
        return True
    return "list" in parse_qs(parts.query)


async def announce_playlist(
    chat_id: int, tracks: list, lang_dict: dict, title: str = None
) -> None:
    """Queue every remaining track and let the chat know what got added —
    inline for short playlists, as a Telegra.ph page for long ones."""
    # Every track from a playlist needs the same duration check a single
    # /play would get, and the total queue still has to respect
    # QUEUE_LIMIT — otherwise a playlist add can bypass both limits.
    tracks = [t for t in tracks if t.duration_sec <= config.DURATION_LIMIT]
    room = max(config.QUEUE_LIMIT - len(queue.get_queue(chat_id)), 0)
    tracks = tracks[:room]

    if not tracks:
        return

    positions = [queue.add(chat_id, track) for track in tracks]
    count = len(tracks)

    if count > PLAYLIST_WEB_THRESHOLD:
        url = await telegraph.create_playlist_page(title or "Playlist", tracks)
        if url:
            return await app.send_message(
                chat_id=chat_id,
                text=lang_dict["playlist_queued"].format(count),
                reply_markup=buttons.playlist_web(
                    url, lang_dict.get("playlist_view", "📜 View full playlist")
                ),
            )

    text = "<blockquote expandable>"
    # Truncate on whole-line boundaries, not a raw character count —
    # each line is a complete, self-contained unit (one escaped title),
    # so this can never cut through the middle of an HTML entity like
    # &amp; (which a raw character slice could, breaking Telegram's
    # HTML parser for the whole message).
    body = ""
    for pos, track in zip(positions, tracks):
        line = f"<b>{pos}.</b> {utils.esc(track.title)}\n"
        if len(body) + len(line) > 1948:
            break
        body += line
    text += body + "</blockquote>"
    await app.send_message(
        chat_id=chat_id,
        text=lang_dict["playlist_queued"].format(count) + text,
    )

@app.on_message(
    filters.command(["play", "playforce", "vplay", "vplayforce", "playmusic", "playmusicforce"])
    & filters.group
    & ~app.bl_users
)
@lang.language()
@checkUB
async def play_hndlr(
    _,
    m: types.Message,
    force: bool = False,
    m3u8: bool = False,
    video: bool = False,
    url: str = None,
    music: bool = False,
) -> None:
    sent = await m.reply_text(m.lang["play_searching"])
    file = None
    mention = m.from_user.mention
    media = tg.get_media(m.reply_to_message) if m.reply_to_message else None
    tracks = []
    playlist_title = None

    if media:
        setattr(sent, "lang", m.lang)
        file = await tg.download(m.reply_to_message, sent)

    elif m3u8:
        file = await tg.process_m3u8(url, sent.id, video)

    elif url:
        if _is_playlist_url(url):
            await sent.edit_text(m.lang["playlist_fetch"])
            tracks, playlist_title = await yt.playlist(
                config.PLAYLIST_LIMIT, mention, url, video
            )

            if not tracks:
                return await sent.edit_text(m.lang["playlist_error"])

            file = tracks[0]
            tracks.remove(file)
            file.message_id = sent.id
        else:
            file = await yt.search(url, sent.id, video=video, music=music)

        if not file:
            return await sent.edit_text(
                m.lang["play_not_found"].format(config.SUPPORT_CHAT)
            )

    elif len(m.command) >= 2:
        query = " ".join(m.command[1:])
        file = await yt.search(query, sent.id, video=video, music=music)
        if not file:
            return await sent.edit_text(
                m.lang["play_not_found"].format(config.SUPPORT_CHAT)
            )

    if not file:
        return await sent.edit_text(m.lang["play_usage"])

    if file.duration_sec > config.DURATION_LIMIT:
        return await sent.edit_text(
            m.lang["play_duration_limit"].format(config.DURATION_LIMIT // 60)
        )

    if await db.is_logger():
        await utils.play_log(m, sent.link, file.title, file.duration)

    file.user = mention
    if force:
        queue.force_play_new(m.chat.id, file)
    else:
        # Re-check the limit here, not just checkUB's upfront check —
        # fetching a playlist takes real time, during which the queue
        # can fill up (another /play, or simple concurrent requests),
        # and checkUB's single check at the very start of the command
        # can't see that. Without this, the playlist's first track
        # could still slip in over the limit even though a normal
        # single-track /play issued at that same moment would
        # correctly be rejected by checkUB.
        if len(queue.get_queue(m.chat.id)) >= config.QUEUE_LIMIT:
            return await sent.edit_text(
                m.lang["play_queue_full"].format(config.QUEUE_LIMIT)
            )
        position = queue.add(m.chat.id, file)

        if position != 0 or await db.get_call(m.chat.id):
            await sent.edit_text(
                m.lang["play_queued"].format(
                    position,
                    utils.esc(file.url),
                    utils.esc(file.title),
                    file.duration,
                    m.from_user.mention,
                ),
                reply_markup=buttons.play_queued(
                    m.chat.id, position, file.id, m.lang["play_now"]
                ),
            )
            if tracks:
                await announce_playlist(m.chat.id, tracks, m.lang, playlist_title)
            return

    stream_headers = None
    direct_stream_used = False
    if not file.file_path:
        if config.EXPERIMENTAL_DIRECT_STREAM and isinstance(file, Track) and not video:
            # Hybrid playback: try a direct HTTPS audio stream first for
            # near-zero disk/startup latency; fall back to a local download
            # automatically if the signed URL cannot be played.
            result = await yt.get_stream_url(file.id)
            if result:
                file.file_path, stream_headers = result
                direct_stream_used = bool(file.file_path and str(file.file_path).startswith("http"))
        if not file.file_path:
            await sent.edit_text(m.lang["play_downloading"])
            file.file_path = await yt.download(file.id, video=video)

    started = await anon.play_media(
        chat_id=m.chat.id, message=sent, media=file, stream_headers=stream_headers
    )

    # Direct signed URLs are fast but short-lived. If Telegram/FFmpeg rejects
    # one, transparently switch to the durable local-download path and retry
    # once instead of making the user run /play again.
    if not started and direct_stream_used and isinstance(file, Track):
        logger.warning("Direct stream failed for %s; falling back to local download", file.id)
        try:
            file.file_path = await yt.download(file.id, video=video)
            stream_headers = None
            if file.file_path:
                started = await anon.play_media(
                    chat_id=m.chat.id, message=sent, media=file, stream_headers=None
                )
        except Exception:
            logger.exception("Download fallback failed for %s", file.id)

    if not started:
        # The track was already placed at queue position 0, so a failed
        # initial start must not leave a dead item blocking the queue.
        current = queue.get_current(m.chat.id)
        if current is file:
            queue.remove_current(m.chat.id)
        return
    if not tracks:
        return
    await announce_playlist(m.chat.id, tracks, m.lang, playlist_title)
