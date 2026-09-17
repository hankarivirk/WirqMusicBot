# Wirq Music Bot - High-Resilience PyTgCalls Controller
# Bot Name: Wirq Music Bot
# Owner: @wirq4 | Support: @wirqbots | GitHub: Hankarivirk/WirqMusicbot

import os
import time
import asyncio
from typing import Optional, Dict, Any, List

from ntgcalls import (
    ConnectionNotFound,
    TelegramServerError,
    RTMPStreamingUnsupported,
    ConnectionError,
    TransportParseException,
)
from pyrogram.errors import (
    ChatSendMediaForbidden,
    ChatSendPhotosForbidden,
    MessageIdInvalid,
)
from pyrogram.types import InputMediaPhoto, Message
from pytgcalls import PyTgCalls, exceptions, types
from pytgcalls.pytgcalls_session import PyTgCallsSession

from wirq import (
    app,
    config,
    db,
    lang,
    logger,
    queue,
    thumb,
    userbot,
    yt,
)
from wirq.helpers import Media, Track, buttons, utils

class TgCall(PyTgCalls):
    def __init__(self):
        self.clients: List[PyTgCalls] = []
        self.recommend_state: Dict[int, dict] = {}
        self.start_times: Dict[int, float] = {}
        self.retry_counts: Dict[int, int] = {}

    async def pause(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        if client is None:
            await self.stop(chat_id)
            return False
        await db.playing(chat_id, paused=True)
        try:
            return await client.pause(chat_id)
        except (ConnectionNotFound, exceptions.NotInCallError, AttributeError):
            await self.stop(chat_id)
            return False

    async def resume(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        if client is None:
            await self.stop(chat_id)
            return False
        await db.playing(chat_id, paused=False)
        try:
            return await client.resume(chat_id)
        except (ConnectionNotFound, exceptions.NotInCallError, AttributeError):
            await self.stop(chat_id)
            return False

    async def stop(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        if client is None:
            return False
        await db.remove_call(chat_id)
        queue.clear(chat_id)
        self.start_times.pop(chat_id, None)
        self.retry_counts.pop(chat_id, None)
        try:
            return await client.leave_call(chat_id)
        except (ConnectionNotFound, exceptions.NotInCallError, AttributeError):
            return False

    async def leave(self, chat_id: int) -> bool:
        """Leave voice chat completely and reset state."""
        return await self.stop(chat_id)

    async def clear(self, chat_id: int) -> None:
        """Empty the group's queue without halting current track."""
        queue.clear_upcoming(chat_id)

    async def replay(self, chat_id: int) -> None:
        current = queue.get_current(chat_id)
        if current:
            _lang = await lang.get_lang(chat_id)
            msg = await app.send_message(chat_id=chat_id, text=_lang.get("replay_track", "🔄 Replaying track..."))
            await self.play_media(chat_id, msg, current, seek_time=0)

    async def volume(self, chat_id: int, vol: int) -> bool:
        client = await db.get_assistant(chat_id)
        if client is None:
            return False
        vol = max(min(vol, 100), 1)
        await db.set_volume(chat_id, vol)
        try:
            return await client.change_volume_call(chat_id, vol)
        except Exception as e:
            logger.warning(f"Error adjusting volume in {chat_id}: {e}")
            return False

    async def seek(self, chat_id: int, to_sec: int) -> bool:
        current = queue.get_current(chat_id)
        if not current:
            return False
        _lang = await lang.get_lang(chat_id)
        msg = await app.send_message(chat_id=chat_id, text=_lang.get("seek_track", f"⏩ Seeking to {to_sec}s..."))
        await self.play_media(chat_id, msg, current, seek_time=to_sec)
        return True

    async def play_media(
        self,
        chat_id: int,
        message: Message,
        media: Media | Track,
        seek_time: int = 0,
        stream_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        client = await db.get_assistant(chat_id)
        if client is None:
            await message.edit_text("❌ Voice chat assistant client is not available. Please ensure your SESSION string is configured.")
            return await self.stop(chat_id)

        _lang = await lang.get_lang(chat_id)

        if not media.file_path:
            await message.edit_text(_lang.get("error_no_file", "❌ Stream file could not be prepared.").format(config.SUPPORT_CHAT))
            return await self.play_next(chat_id)

        bass_level = await db.get_bass(chat_id)
        ffmpeg_parts = []
        if seek_time > 1:
            ffmpeg_parts.append(f"-ss {seek_time}")
        if bass_level:
            ffmpeg_parts.append(f"-af bass=g={bass_level}")

        # Construct stream with audio/video mode handling (Section 1)
        stream = types.MediaStream(
            media_path=media.file_path,
            audio_parameters=types.AudioQuality.HIGH,
            video_parameters=types.VideoQuality.HD_720p,
            audio_flags=types.MediaStream.Flags.REQUIRED,
            video_flags=(
                types.MediaStream.Flags.AUTO_DETECT
                if media.video
                else types.MediaStream.Flags.IGNORE
            ),
            ffmpeg_parameters=" ".join(ffmpeg_parts) if ffmpeg_parts else None,
        )

        try:
            await client.play(
                chat_id=chat_id,
                stream=stream,
                config=types.GroupCallConfig(auto_start=False),
            )
            if not seek_time:
                media.time = 1
                await queue.remember(chat_id, media.id)
                await db.add_call(chat_id)
                await db.track_played()
                self.start_times[chat_id] = time.time()

            # Retrieve dynamic status for player card
            loop_mode = await db.get_loop(chat_id)
            loop_str = "OFF" if loop_mode == 0 else ("SONG" if loop_mode == 1 else "QUEUE")
            auto_str = "ON" if await db.get_autoplay(chat_id) else "OFF"
            req_user = getattr(media, "user", None) or "@wirq4"

            # Check thumbnail priority: Group > Global > ENV (Section 6)
            use_thumb = await db.is_thumb_enabled(chat_id)
            card_path = None
            if use_thumb and isinstance(media, Track):
                try:
                    card_path = await thumb.generate(
                        track=media,
                        elapsed_sec=seek_time,
                        is_video=media.video,
                        codec="OPUS" if not media.video else "H.264/AAC",
                        bitrate="160 KBPS" if not media.video else "720p HD",
                        video_quality="720p HD",
                        loop_status=loop_str,
                        autoplay_status=auto_str,
                    )
                except Exception as e:
                    logger.warning(f"Thumbnail generation error: {e}")

            mode_label = "Video 720p HD" if media.video else "Audio Lossless (160kbps)"
            caption = (
                f"<b>🎵 Now Streaming:</b> <a href='{media.url}'>{media.title}</a>\n\n"
                f"• <b>Artist:</b> <code>{media.channel_name}</code>\n"
                f"• <b>Duration:</b> <code>{media.duration}</code>\n"
                f"• <b>Mode:</b> <code>{mode_label}</code>\n"
                f"• <b>Loop:</b> <code>{loop_str}</code> | <b>Autoplay:</b> <code>{auto_str}</code>\n"
                f"• <b>Requested by:</b> {req_user}\n\n"
                f"<i>Powered by {config.BRAND_NAME}</i>"
            )
            markup = buttons.controls(chat_id=chat_id)

            try:
                if card_path and os.path.exists(card_path):
                    sent = await app.send_photo(
                        chat_id=chat_id,
                        photo=card_path,
                        caption=caption,
                        reply_markup=markup,
                    )
                else:
                    sent = await app.send_message(
                        chat_id=chat_id,
                        text=caption,
                        reply_markup=markup,
                        disable_web_page_preview=True,
                    )
                media.message_id = sent.id
                # Delete initial loading message
                try:
                    await message.delete()
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"Failed to send player card: {e}")

        except Exception as e:
            logger.error(f"Playback initiation error in {chat_id}: {e}")
            await message.edit_text(f"❌ Playback error: <code>{e}</code>")
            await self.play_next(chat_id)

    async def play_next(self, chat_id: int) -> None:
        loop_mode = await db.get_loop(chat_id)
        current = queue.get_current(chat_id)

        # 1. Loop current song (Section 3: Loop State 1)
        if loop_mode == 1 and current:
            return await self.replay(chat_id)

        # 2. Loop entire queue (Section 3: Loop State 2)
        if loop_mode == 2 and current:
            # Re-queue finished track to end of playlist
            queue.put(chat_id, current)

        async with queue.lock(chat_id):
            media = queue.get_next(chat_id)

            # Cleanup previous now-playing message
            try:
                if current and current.message_id:
                    await app.delete_messages(
                        chat_id=chat_id,
                        message_ids=current.message_id,
                        revoke=True,
                    )
                    current.message_id = 0
            except Exception:
                pass

            # If queue empty, handle Autoplay (Section 4)
            if not media and current and isinstance(current, Track):
                is_autoplay = await db.get_autoplay(chat_id)
                if is_autoplay:
                    # Autoplay ON: Auto-fetch real YouTube related track
                    media = await yt.related(current.id, exclude=await queue.get_history(chat_id))
                    if media:
                        setattr(media, "user", "⚡ Autoplay Engine")
                        queue.put(chat_id, media)
                        media = queue.get_next(chat_id)
                else:
                    # Autoplay OFF: Display 3 real YouTube recommendations + "More" button
                    from py_yt import Recommendations
                    recs = await Recommendations.get(current.id, limit=12)
                    if recs:
                        self.recommend_state[chat_id] = {
                            "recs": recs,
                            "offset": 0,
                            "video_id": current.id,
                        }
                        markup = buttons.recommend_markup(recs[:3], "🔄 More Recommendations")
                        await app.send_message(
                            chat_id=chat_id,
                            text=(
                                "🎧 <b>Playback finished. Here are real YouTube recommendations:</b>\n"
                                "<i>Tap any track below to start streaming, or tap More for fresh picks.</i>"
                            ),
                            reply_markup=markup,
                        )
                    return await self.stop(chat_id)

            if not media:
                return await self.stop(chat_id)

            _lang = await lang.get_lang(chat_id)
            msg = await app.send_message(chat_id=chat_id, text=_lang.get("play_next", "⏳ Loading next track..."))

            # Automatic Stream Expiry Handling & Resolution (Section 1)
            retry_count = 0
            while not media.file_path and retry_count < 3:
                try:
                    media.file_path = await yt.download(media.id, video=media.video)
                    if media.file_path:
                        break
                except Exception as e:
                    logger.warning(f"Download attempt {retry_count + 1} failed for {media.id}: {e}")
                retry_count += 1
                await asyncio.sleep(1)

            if not media.file_path:
                await msg.edit_text(f"⚠️ Failed to stream <b>{media.title}</b> after retries. Skipping...")
                return await self.play_next(chat_id)

            return await self.play_media(chat_id, msg, media)

    async def ping(self) -> float:
        if not self.clients:
            return 0.0
        pings = [client.ping for client in self.clients]
        return round(sum(pings) / len(pings), 2)

    async def decorators(self, client: PyTgCalls) -> None:
        @client.on_update()
        async def update_handler(_, update: types.Update) -> None:
            if isinstance(update, types.StreamEnded):
                if update.stream_type == types.StreamEnded.Type.AUDIO:
                    await self.play_next(update.chat_id)
            elif isinstance(update, types.ChatUpdate):
                if update.status in [
                    types.ChatUpdate.Status.KICKED,
                    types.ChatUpdate.Status.LEFT_GROUP,
                    types.ChatUpdate.Status.CLOSED_VOICE_CHAT,
                ]:
                    await self.stop(update.chat_id)

    async def boot(self) -> None:
        PyTgCallsSession.notice_displayed = True
        for ub in userbot.clients:
            client = PyTgCalls(ub, cache_duration=100)
            await client.start()
            self.clients.append(client)
            await self.decorators(client)
        logger.info("PyTgCalls client(s) started successfully.")
