# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


from ntgcalls import (ConnectionNotFound, TelegramServerError,
                      RTMPStreamingUnsupported, ConnectionError,
                      TransportParseException)
from pyrogram.errors import (ChatSendMediaForbidden, ChatSendPhotosForbidden,
                             MessageIdInvalid)
from pyrogram.types import InputMediaPhoto, Message
from pytgcalls import PyTgCalls, exceptions, types
from pytgcalls.pytgcalls_session import PyTgCallsSession

import asyncio

from anony import (app, config, db, lang, logger,
                   queue, thumb, userbot, yt)
from anony.helpers import Media, Track, buttons, utils


class TgCall(PyTgCalls):
    def __init__(self):
        self.clients = []
        # Per-chat state for the "up next" recommendation cards shown
        # when the queue ends with autoplay on: which track they were
        # generated from, which IDs have already been offered (so
        # "More" doesn't repeat them), and the actual Track objects
        # (keyed by id) so a button tap can find what it's picking.
        # In-memory only — a restart just means a stale card can no
        # longer be acted on, which is fine.
        self.recommend_state: dict[int, dict] = {}

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

    async def stop(self, chat_id: int) -> None:
        had_call = await db.get_call(chat_id)
        queue.clear(chat_id)
        await queue.clear_history(chat_id)
        await db.remove_call(chat_id)
        await db.set_loop(chat_id, 0)

        if not had_call:
            # Nothing was actually active for this chat, so don't fetch (and
            # potentially assign/persist) an assistant client just to leave
            # a call that never existed.
            return

        client = await db.get_assistant(chat_id)
        try:
            await client.leave_call(chat_id, close=False)
        except Exception:
            pass


    async def play_media(
        self,
        chat_id: int,
        message: Message,
        media: Media | Track,
        seek_time: int = 0,
    ) -> None:
        client = await db.get_assistant(chat_id)
        _lang = await lang.get_lang(chat_id)
        _thumb = (
            await thumb.generate(media)
            if isinstance(media, Track)
            else config.DEFAULT_THUMB
        ) if config.THUMB_GEN else None

        if not media.file_path:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            return await self.play_next(chat_id)

        bass_level = await db.get_bass(chat_id)
        ffmpeg_parts = []
        if seek_time > 1:
            ffmpeg_parts.append(f"-ss {seek_time}")
        if bass_level:
            # FFmpeg's `bass` audio filter, boosting low frequencies by
            # bass_level dB. No quotes around the filter value: those
            # are shell-quoting syntax for typing in a terminal, and do
            # nothing useful (in fact actively break things) once this
            # string is split into a plain argument list rather than
            # run through an actual shell — `bass=g=10` has no spaces,
            # so it never needed quoting in the first place.
            ffmpeg_parts.append(f"-af bass=g={bass_level}")

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
                self._background_prep(chat_id, media)
                text = _lang["play_media"].format(
                    utils.esc(media.url),
                    utils.esc(media.title),
                    media.duration,
                    media.user,
                )
                keyboard = buttons.controls(chat_id)
                try:
                    if _thumb:
                        await message.edit_media(
                            media=InputMediaPhoto(
                                media=_thumb,
                                caption=text,
                            ),
                            reply_markup=keyboard,
                        )
                    else:
                        await message.edit_text(text, reply_markup=keyboard)
                except (ChatSendMediaForbidden, ChatSendPhotosForbidden, MessageIdInvalid):
                    if _thumb:
                        sent = await app.send_photo(
                            chat_id=chat_id,
                            photo=_thumb,
                            caption=text,
                            reply_markup=keyboard,
                        )
                    else:
                        sent = await app.send_message(
                            chat_id=chat_id,
                            text=text,
                            reply_markup=keyboard,
                        )
                    media.message_id = sent.id
        except FileNotFoundError:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            await self.play_next(chat_id)
        except exceptions.NoActiveGroupCall:
            await self.stop(chat_id)
            await message.edit_text(_lang["error_no_call"])
        except exceptions.NoAudioSourceFound:
            await message.edit_text(_lang["error_no_audio"])
            await self.play_next(chat_id)
        except (ConnectionError, ConnectionNotFound, TelegramServerError,
                TransportParseException, TimeoutError):
            await self.stop(chat_id)
            await message.edit_text(_lang["error_tg_server"])
        except RTMPStreamingUnsupported:
            await self.stop(chat_id)
            await message.edit_text(_lang["error_rtmp"])


    def _background_prep(self, chat_id: int, media: Media | Track) -> None:
        """Fire-and-forget: never awaited, never blocks playback."""
        asyncio.create_task(self._prefetch_next(chat_id))

    async def _prefetch_next(self, chat_id: int) -> None:
        """Runs alongside playback, not before it. Peeks (without
        popping) the next queued track and, if it doesn't have a file
        yet, downloads it now — so by the time the current track ends,
        play_next() finds it already sitting on disk instead of
        blocking on a download at every transition. Always a full
        download (never a direct CDN-URL stream — that caused silent/
        no-audio playback when tried for the currently-playing track)."""
        upcoming = queue.get_next(chat_id, check=True)
        if isinstance(upcoming, Track) and not upcoming.file_path:
            try:
                upcoming.file_path = await yt.download(upcoming.id, video=upcoming.video)
            except Exception as e:
                logger.warning(f"Prefetch failed for {upcoming.id}: {e}")

    async def replay(self, chat_id: int) -> None:
        if not await db.get_call(chat_id):
            return

        media = queue.get_current(chat_id)
        if not media:
            # Nothing queued to replay (e.g. loop was set but the queue
            # emptied out from under us); fall back to stopping cleanly
            # instead of crashing on media.message_id below.
            return await self.stop(chat_id)

        _lang = await lang.get_lang(chat_id)
        msg = await app.send_message(chat_id=chat_id, text=_lang["play_again"])
        media.message_id = msg.id
        await self.play_media(chat_id, msg, media)


    async def autoplay_next(self, chat_id: int, current: Media | Track) -> Track | None:
        """Look up a related "up next" track and queue it automatically,
        skipping anything already played or already in the queue, and
        never repeating the track that just finished. This is what
        runs when autoplay is ON. When it's OFF, play_next() calls
        send_recommendations() instead so the user picks."""
        if not current or not isinstance(current, Track):
            return None

        exclude = (await queue.excluded_ids(chat_id)) | {current.id}
        track = await yt.related(current.id, exclude)
        if not track:
            return None

        track.user = "Autoplay"
        queue.add(chat_id, track)
        return queue.get_current(chat_id)

    async def send_recommendations(
        self, chat_id: int, seed_id: str, message: Message | None = None
    ) -> bool:
        """Send (or, for a "More" tap, refresh) a card of up-to-3
        related tracks for the user to pick from — YouTube's own
        "up next" panel, basically. Shown when the queue ends with
        autoplay OFF, instead of just going silent. (Autoplay ON skips
        this entirely and keeps playing automatically via
        autoplay_next().) Returns True if a card was shown, False if
        there was nothing left to recommend (caller should fall back
        to just stopping)."""
        state = self.recommend_state.get(chat_id)
        shown = set(state["shown"]) if state and state.get("seed") == seed_id else set()

        excluded = (await queue.excluded_ids(chat_id)) | {seed_id} | shown
        tracks = await yt.related_batch(seed_id, excluded, count=3)

        _lang = await lang.get_lang(chat_id)
        if not tracks:
            self.recommend_state.pop(chat_id, None)
            text = _lang["recommend_none"]
            if message:
                try:
                    await message.edit_text(text)
                    return False
                except Exception:
                    pass
            await app.send_message(chat_id=chat_id, text=text)
            return False

        shown |= {t.id for t in tracks}
        self.recommend_state[chat_id] = {
            "seed": seed_id,
            "shown": shown,
            "tracks": {t.id: t for t in tracks},
        }

        markup = buttons.recommend_markup(tracks, _lang["recommend_more"])
        text = _lang["recommend_title"]
        if message:
            try:
                await message.edit_text(text, reply_markup=markup)
                return True
            except Exception:
                pass
        await app.send_message(chat_id=chat_id, text=text, reply_markup=markup)
        return True

    async def play_next(self, chat_id: int) -> None:
        if loop := await db.get_loop(chat_id):
            await db.set_loop(chat_id, loop - 1)
            return await self.replay(chat_id)

        # Loop instead of recursing on download failures, and only hold the
        # per-chat lock around the queue mutation itself (not across the
        # download/play_media call) so play_media's own retries into
        # play_next can't deadlock on a lock this call already holds.
        while True:
            async with queue.lock(chat_id):
                current = queue.get_current(chat_id)
                media = queue.get_next(chat_id)

                try:
                    # Delete the *previous* now-playing message (current),
                    # not the upcoming track's message (media), which may
                    # not even exist yet.
                    if current and current.message_id:
                        await app.delete_messages(
                            chat_id=chat_id,
                            message_ids=current.message_id,
                            revoke=True,
                        )
                        current.message_id = 0
                except Exception:
                    pass

                if not media and current and isinstance(current, Track):
                    if await db.get_autoplay(chat_id):
                        # Autoplay ON: keep the music going automatically,
                        # no prompt — the classic autoplay behavior.
                        media = await self.autoplay_next(chat_id, current)
                    elif await self.send_recommendations(chat_id, current.id):
                        # Autoplay OFF: queue's empty, so offer a pick-one
                        # card (YouTube's "up next" style) instead of just
                        # going silent.
                        return
                    # Either autoplay found nothing, or there was nothing
                    # left to recommend — fall through to stop() below.

                if not media:
                    return await self.stop(chat_id)

            _lang = await lang.get_lang(chat_id)
            msg = await app.send_message(chat_id=chat_id, text=_lang["play_next"])
            if not media.file_path:
                # Usually already sitting on disk from the background
                # prefetch that started when the previous track began
                # playing. If it isn't ready yet, just download it now —
                # full download, not a direct CDN-URL stream (that
                # caused silent/no-audio playback).
                media.file_path = await yt.download(media.id, video=media.video)
                if not media.file_path:
                    await msg.edit_text(
                        _lang["error_no_file"].format(config.SUPPORT_CHAT)
                    )
                    continue

            media.message_id = msg.id
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
        logger.info("PyTgCalls client(s) started.")
