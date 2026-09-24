import logging
from pyrogram import filters
from pyrogram.types import Message
from anony import app
import config
from anony.core.calls import MusicCall
from anony.core.youtube import YouTube, resolve_playlist_url, is_youtube_url
from anony.helpers._admins import is_admin
from anony.helpers._inline import stream_markup, queued_markup
from anony.helpers._queue import Queues
from anony.utils.database import (
    is_blacklisted,
    is_playmode_admin,
    should_show_youtube_thumbnail,
)

LOGGER = logging.getLogger("MusicFlow.Play")

@app.on_message(filters.command(["play", "vplay"]) & filters.group)
async def play_handler(_, message: Message):
    chat_id = message.chat.id
    if await is_blacklisted(chat_id):
        return

    # Check playmode
    if await is_playmode_admin(chat_id) and not await is_admin(message):
        return await message.reply_text("I need administrator access to control playback here.")

    if len(message.command) < 2:
        return await message.reply_text("Type a song, artist, or album.")

    raw_query = message.text.split(None, 1)[1].strip()
    is_force = False
    is_video = message.command[0].startswith("v")

    if raw_query.startswith("-f "):
        is_force = True
        raw_query = raw_query[3:].strip()
    elif raw_query.startswith("-v "):
        is_video = True
        raw_query = raw_query[3:].strip()

    requester = message.from_user.mention if message.from_user else "User"

    # 1. Playlist / Mix Detection
    if resolve_playlist_url(raw_query):
        status_msg = await message.reply_text("⌁ Loading playlist...")
        pl_title, tracks = await YouTube.get_playlist(raw_query, limit=config.PLAYLIST_FETCH_LIMIT)
        if not tracks:
            return await status_msg.edit_text("Couldn't load that playlist.\n\nTry again with another link.")

        for t in tracks:
            t["requester"] = requester
            t["video"] = is_video

        if not MusicCall.active_tracks.get(chat_id) or is_force:
            first_track = tracks[0]
            success = await MusicCall.play(chat_id, first_track)
            for rem in tracks[1:]:
                Queues.add_to_queue(chat_id, rem)

            await status_msg.delete()
            if success:
                artist = first_track.get("channel") or first_track.get("channel_name") or "YouTube"
                dur = first_track.get("duration") or "Unknown"
                now_text = (
                    "Now playing\n\n"
                    f"{first_track['title']}\n"
                    f"{artist}\n\n"
                    f"Requested by {requester}\n"
                    f"Duration: {dur}"
                )
                markup = stream_markup(chat_id)
                show_thumb = await should_show_youtube_thumbnail(chat_id)
                thumb_url = first_track.get("thumbnail")

                if show_thumb and thumb_url:
                    try:
                        return await message.reply_photo(photo=thumb_url, caption=now_text, reply_markup=markup)
                    except Exception:
                        pass
                await message.reply_text(now_text, reply_markup=markup)
            else:
                await message.reply_text("That track couldn't be played right now.\n\nTry another track or search for the same song again.")
        else:
            for t in tracks:
                Queues.add_to_queue(chat_id, t)
            await status_msg.edit_text(f"Playlist added.\n\n{len(tracks)} tracks queued.")
        return

    # 2. Single Track Search & Playback
    is_url = is_youtube_url(raw_query) or raw_query.startswith("http://") or raw_query.startswith("https://")
    if is_url:
        status_msg = await message.reply_text("Link received.\n\nResolving the track...")
    else:
        status_msg = await message.reply_text("⌁ Searching...")

    track = await YouTube.search(raw_query, requester=requester)
    if not track:
        if is_url:
            return await status_msg.edit_text("That link isn't supported.\n\nSend a supported music or video link, or search by name.")
        return await status_msg.edit_text("Nothing found.\n\nTry another search.")

    track["video"] = is_video
    track["requester"] = requester
    artist = track.get("channel") or track.get("channel_name") or "YouTube"
    dur = track.get("duration") or "Unknown"

    if not MusicCall.active_tracks.get(chat_id) or is_force:
        await status_msg.edit_text(f"Found it.\n\n{track['title']}\n{artist}\n\nStarting playback...")
        success = await MusicCall.play(chat_id, track)
        await status_msg.delete()
        if not success:
            return await message.reply_text("That track couldn't be played right now.\n\nTry another track or search for the same song again.")

        now_text = (
            "Now playing\n\n"
            f"{track['title']}\n"
            f"{artist}\n\n"
            f"Requested by {requester}\n"
            f"Duration: {dur}"
        )
        markup = stream_markup(chat_id)
        show_thumb = await should_show_youtube_thumbnail(chat_id)
        thumb_url = track.get("thumbnail")

        if show_thumb and thumb_url:
            try:
                return await message.reply_photo(photo=thumb_url, caption=now_text, reply_markup=markup)
            except Exception:
                pass
        await message.reply_text(now_text, reply_markup=markup)
    else:
        Queues.add_to_queue(chat_id, track)
        await status_msg.delete()
        queued_text = (
            "Added to queue.\n\n"
            f"{track['title']}\n"
            f"{artist}"
        )
        await message.reply_text(queued_text, reply_markup=queued_markup(chat_id, track["id"]))
