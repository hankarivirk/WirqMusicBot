import asyncio
import logging
import os
import shlex
from typing import Optional

from pyrogram.types import InputMediaPhoto, Message
from pyrogram.errors import ChatSendMediaForbidden, ChatSendPhotosForbidden, MessageIdInvalid
from pytgcalls import PyTgCalls, types
from pytgcalls.exceptions import NoActiveGroupCall

import anony
from anony import config, logger, spawn_task
from anony.helpers import Media, Track, buttons, utils


class TgCall:
    """High-performance voice-chat manager for PyTgCalls 2.3.x.

    Keeps the original Wirq feature set (autoplay/recommendations,
    prefetching, loop, seek, bass, player cards) while using the modern
    PyTgCalls API.
    """

    def __init__(self):
        self.clients: list[PyTgCalls] = []
        self.transition_locks: dict[int, asyncio.Lock] = {}
        self.generations: dict[int, int] = {}
        self.recommend_state: dict[int, dict] = {}
        # Prevent duplicate StreamEnded updates from advancing two tracks
        # at once. Telegram/voice updates can be delivered more than once
        # around reconnects.
        self._next_tasks: dict[int, asyncio.Task] = {}

    def _lock(self, chat_id: int) -> asyncio.Lock:
        lock = self.transition_locks.get(chat_id)
        if lock is None:
            lock = asyncio.Lock()
            self.transition_locks[chat_id] = lock
        return lock

    def _generation(self, chat_id: int) -> int:
        value = self.generations.get(chat_id, 0) + 1
        self.generations[chat_id] = value
        return value

    def _get_generation(self, chat_id: int) -> int:
        return self.generations.get(chat_id, 0)

    def _engine(self, number: int) -> Optional[PyTgCalls]:
        if not self.clients:
            return None
        if 1 <= number <= len(self.clients):
            return self.clients[number - 1]
        return self.clients[0]

    async def _engine_for(self, chat_id: int) -> Optional[PyTgCalls]:
        if not self.clients:
            return None
        number = await anony.db.get_assistant_num(chat_id, len(self.clients))
        return self._engine(number)

    async def pause(self, chat_id: int) -> bool:
        if not self.clients:
            return False
        async with self._lock(chat_id):
            client = await self._engine_for(chat_id)
            if client is None:
                return False
            try:
                await client.pause(chat_id)
                await anony.db.playing(chat_id, paused=True)
                return True
            except Exception:
                logger.debug("Pause failed for %s", chat_id, exc_info=True)
                return False

    async def resume(self, chat_id: int) -> bool:
        if not self.clients:
            return False
        async with self._lock(chat_id):
            client = await self._engine_for(chat_id)
            if client is None:
                return False
            try:
                await client.resume(chat_id)
                await anony.db.playing(chat_id, paused=False)
                return True
            except Exception:
                logger.debug("Resume failed for %s", chat_id, exc_info=True)
                return False

    async def _stop_unlocked(self, chat_id: int) -> bool:
        self._generation(chat_id)
        if self.clients:
            try:
                client = await self._engine_for(chat_id)
                if client:
                    await client.leave_call(chat_id)
            except Exception:
                logger.debug("leave_call failed for %s", chat_id, exc_info=True)

        anony.queue.clear(chat_id)
        await anony.queue.clear_history(chat_id)
        await anony.db.remove_call(chat_id)
        await anony.db.set_loop(chat_id, 0)
        self.recommend_state.pop(chat_id, None)
        return True

    async def stop(self, chat_id: int) -> bool:
        async with self._lock(chat_id):
            return await self._stop_unlocked(chat_id)

    @staticmethod
    def _stream(
        file_path: str,
        video: bool = False,
        seek_time: int = 0,
        bass_level: int = 0,
        headers: dict | None = None,
    ) -> types.MediaStream:
        parts: list[str] = []
        if seek_time > 0:
            parts += ["-ss", str(max(0, seek_time))]
        if bass_level > 0 and not video:
            parts += [
                "-af",
                f"bass=g={max(0, min(15, bass_level))}",
            ]
        if headers:
            block = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
            parts += ["-headers", shlex.quote(block)]
        return types.MediaStream(
            file_path,
            ffmpeg_parameters=" ".join(parts) or None,
        )

    async def play_media(
        self,
        chat_id: int,
        message: Message,
        media: Media | Track,
        seek_time: int = 0,
        stream_headers: dict | None = None,
    ) -> bool:
        # Serialize actual voice-engine replacement with skip/stop/seek
        # operations. The lock is held only for the short playback-start
        # transaction; downloads happen before this method in play_next.
        async with self._lock(chat_id):
            return await self._play_media_unlocked(
                chat_id, message, media, seek_time, stream_headers
            )

    async def _play_media_unlocked(
        self,
        chat_id: int,
        message: Message,
        media: Media | Track,
        seek_time: int = 0,
        stream_headers: dict | None = None,
    ) -> bool:
        generation = self._generation(chat_id)

        if not self.clients:
            try:
                await message.edit_text("❌ Voice engine is unavailable. Try again shortly.")
            except Exception:
                pass
            return False

        if not media.file_path:
            _lang = await anony.lang.get_lang(chat_id)
            try:
                await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            except Exception:
                pass
            return False

        client = await self._engine_for(chat_id)
        if client is None:
            return False

        bass_level = await anony.db.get_bass(chat_id)
        stream = self._stream(
            media.file_path,
            getattr(media, "video", getattr(media, "is_video", False)),
            seek_time,
            bass_level,
            stream_headers,
        )

        try:
            # PyTgCalls 2.3.x uses play() for initial playback and replacement.
            await client.play(chat_id, stream)
        except NoActiveGroupCall:
            await anony.db.remove_call(chat_id)
            try:
                await message.edit_text(anony.lang.languages.get(
                    await anony.db.get_lang(chat_id), {}
                ).get("error_no_call", "❌ No active Voice Chat found."))
            except Exception:
                pass
            return False
        except FileNotFoundError:
            return await self._recover_failed_play(chat_id, message)
        except Exception as exc:
            logger.exception("Playback error in %s: %s", chat_id, exc)
            return False

        if generation != self._get_generation(chat_id):
            return False

        media.time = max(1, seek_time)
        await anony.db.add_call(chat_id)
        anony.queue.set_current(chat_id, media)

        if not seek_time:
            await anony.queue.remember(chat_id, media.id)
            self._background_prep(chat_id, media)

        # Metadata/card work is deliberately detached from the playback path.
        spawn_task(
            self._update_player_card(chat_id, message, media, generation),
            name=f"player-card:{chat_id}",
        )
        return True

    async def _recover_failed_play(self, chat_id: int, message: Message) -> bool:
        try:
            _lang = await anony.lang.get_lang(chat_id)
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
        except Exception:
            pass
        return False

    async def _update_player_card(
        self, chat_id: int, message: Message, media: Media | Track, generation: int
    ):
        if generation != self._get_generation(chat_id):
            return

        _lang = await anony.lang.get_lang(chat_id)
        text = _lang["play_media"].format(
            utils.esc(media.url),
            utils.esc(media.title),
            media.duration,
            media.user,
        )
        keyboard = buttons.controls(chat_id)

        # Per-group thumbnail switch. Global THUMB_GEN only enables the feature;
        # groups explicitly opt in with /thumbnail on.
        thumb_path = None
        if (
            config.THUMB_GEN
            and isinstance(media, Track)
            and await anony.db.get_thumbnail_gen(chat_id)
        ):
            try:
                thumb_path = await anony.thumb.generate(media)
            except Exception:
                thumb_path = None

        if generation != self._get_generation(chat_id):
            return

        try:
            if thumb_path and os.path.isfile(thumb_path):
                try:
                    await message.edit_media(
                        media=InputMediaPhoto(media=thumb_path, caption=text),
                        reply_markup=keyboard,
                    )
                except (ChatSendMediaForbidden, ChatSendPhotosForbidden, MessageIdInvalid):
                    sent = await anony.app.send_photo(
                        chat_id, photo=thumb_path, caption=text, reply_markup=keyboard
                    )
                    media.message_id = sent.id
            else:
                await message.edit_text(text, reply_markup=keyboard)
        except Exception:
            try:
                sent = await anony.app.send_message(
                    chat_id=chat_id, text=text, reply_markup=keyboard
                )
                media.message_id = sent.id
            except Exception:
                logger.debug("Player card failed for %s", chat_id, exc_info=True)

    def _background_prep(self, chat_id: int, media: Media | Track):
        spawn_task(self._cache_and_prefetch(chat_id, media), name=f"prefetch:{chat_id}")

    async def _cache_and_prefetch(self, chat_id: int, media: Media | Track):
        try:
            if isinstance(media, Track) and media.file_path and str(media.file_path).startswith("http"):
                cached = await anony.yt.download(media.id, video=media.video)
                if cached:
                    media.file_path = cached
        except Exception:
            logger.debug("Background cache failed", exc_info=True)

        try:
            upcoming = anony.queue.get_next(chat_id, check=True)
            if isinstance(upcoming, Track) and not upcoming.file_path:
                upcoming.file_path = await anony.yt.download(
                    upcoming.id, video=upcoming.video
                )
        except Exception:
            logger.debug("Prefetch failed", exc_info=True)

    async def replay(self, chat_id: int) -> bool:
        if not await anony.db.get_call(chat_id):
            return False
        media = anony.queue.get_current(chat_id)
        if not media:
            return await self.stop(chat_id)
        _lang = await anony.lang.get_lang(chat_id)
        msg = await anony.app.send_message(chat_id, _lang["play_again"])
        media.message_id = msg.id
        return await self.play_media(chat_id, msg, media)

    async def autoplay_next(self, chat_id: int, current: Media | Track) -> Track | None:
        if not isinstance(current, Track) or not current.id:
            return None
        excluded = await anony.queue.excluded_ids(chat_id)
        excluded.add(current.id)
        track = await anony.yt.related(current.id, excluded)
        if not track:
            return None
        track.user = "Autoplay"
        anony.queue.add(chat_id, track)
        return track

    async def send_recommendations(
        self, chat_id: int, seed_id: str, message: Message | None = None
    ) -> bool:
        state = self.recommend_state.get(chat_id)
        shown = set(state["shown"]) if state and state.get("seed") == seed_id else set()
        excluded = (await anony.queue.excluded_ids(chat_id)) | {seed_id} | shown
        tracks = await anony.yt.related_batch(seed_id, excluded, count=3)
        _lang = await anony.lang.get_lang(chat_id)

        if not tracks:
            self.recommend_state.pop(chat_id, None)
            text = _lang.get("recommend_none", "No more recommendations.")
            if message:
                try:
                    await message.edit_text(text)
                except Exception:
                    pass
            else:
                await anony.app.send_message(chat_id, text)
            return False

        shown |= {t.id for t in tracks}
        self.recommend_state[chat_id] = {
            "seed": seed_id,
            "shown": shown,
            "tracks": {t.id: t for t in tracks},
        }
        markup = buttons.recommend_markup(
            tracks, _lang.get("recommend_more", "More recommendations")
        )
        text = _lang.get("recommend_title", "Up next")
        if message:
            try:
                await message.edit_text(text, reply_markup=markup)
                return True
            except Exception:
                pass
        await anony.app.send_message(chat_id, text, reply_markup=markup)
        return True

    async def play_next(self, chat_id: int) -> bool:
        failures = 0
        while failures < 5:
            async with self._lock(chat_id):
                loop_count = await anony.db.get_loop(chat_id)
                current = anony.queue.get_current(chat_id)

                if loop_count and current:
                    await anony.db.set_loop(chat_id, loop_count - 1)
                    media = current
                else:
                    media = anony.queue.get_next(chat_id)

                if not media and current and isinstance(current, Track):
                    if await anony.db.get_autoplay(chat_id):
                        media = await self.autoplay_next(chat_id, current)
                    elif await self.send_recommendations(chat_id, current.id):
                        return True

                if not media:
                    await self._stop_unlocked(chat_id)
                    return False

                try:
                    if current and current.message_id:
                        await anony.app.delete_messages(
                            chat_id, current.message_id, revoke=True
                        )
                        current.message_id = 0
                except Exception:
                    pass

                _lang = await anony.lang.get_lang(chat_id)
                msg = await anony.app.send_message(chat_id, _lang["play_next"])

                headers = None
                direct_stream_used = False
                if not media.file_path:
                    if (
                        config.EXPERIMENTAL_DIRECT_STREAM
                        and isinstance(media, Track)
                        and not media.video
                    ):
                        try:
                            result = await anony.yt.get_stream_url(media.id)
                            if result:
                                media.file_path, headers = result
                                direct_stream_used = bool(
                                    media.file_path
                                    and str(media.file_path).startswith("http")
                                )
                        except Exception:
                            headers = None

                    if not media.file_path:
                        media.file_path = await anony.yt.download(
                            media.id, video=media.video
                        )

                if not media.file_path:
                    failures += 1
                    try:
                        await msg.edit_text(
                            _lang["error_no_file"].format(config.SUPPORT_CHAT)
                        )
                    except Exception:
                        pass
                    continue

                media.message_id = msg.id
                # Do not hold the transition lock during FFmpeg/network startup.
                # Release it first so callbacks remain responsive.
            started = await self.play_media(
                chat_id, msg, media, stream_headers=headers
            )

            if started:
                return True

            # A signed CDN URL can expire or be rejected by FFmpeg even when
            # extraction succeeded. Retry once through the durable local-file
            # path so autoplay does not die on a transient direct-stream failure.
            if direct_stream_used and isinstance(media, Track):
                try:
                    media.file_path = await anony.yt.download(
                        media.id, video=media.video
                    )
                    if media.file_path:
                        started = await self.play_media(
                            chat_id, msg, media, stream_headers=None
                        )
                        if started:
                            return True
                except Exception:
                    logger.exception(
                        "Local fallback failed for queued track %s", media.id
                    )

            failures += 1

        await anony.app.send_message(
            chat_id,
            (await anony.lang.get_lang(chat_id)).get(
                "play_too_many_failures",
                "❌ Too many failed tracks. Playback stopped.",
            ),
        )
        await self.stop(chat_id)
        return False

    async def ping(self) -> float:
        if not self.clients:
            return 0.0
        values = [getattr(c, "ping", 0.0) for c in self.clients]
        return round(sum(values) / max(len(values), 1), 2)

    async def _register(self, client: PyTgCalls):
        @client.on_update()
        async def update_handler(_, update):
            if isinstance(update, types.StreamEnded):
                # Only audio end advances the music anony.queue. Video/audio-video
                # streams can be handled by the same end signal when audio exists.
                if getattr(update, "stream_type", None) in (
                    getattr(types.StreamEnded.Type, "AUDIO", None),
                    getattr(types.StreamEnded.Type, "VIDEO", None),
                ):
                    existing = self._next_tasks.get(update.chat_id)
                    if existing is None or existing.done():
                        task = spawn_task(
                            self.play_next(update.chat_id),
                            name=f"play-next:{update.chat_id}",
                        )
                        self._next_tasks[update.chat_id] = task

                        def _clear_next(done, chat_id=update.chat_id):
                            if self._next_tasks.get(chat_id) is done:
                                self._next_tasks.pop(chat_id, None)

                        task.add_done_callback(_clear_next)
            elif isinstance(update, types.ChatUpdate):
                status = getattr(update, "status", None)
                closed = {
                    getattr(types.ChatUpdate.Status, "KICKED", None),
                    getattr(types.ChatUpdate.Status, "LEFT_GROUP", None),
                    getattr(types.ChatUpdate.Status, "CLOSED_VOICE_CHAT", None),
                }
                if status in closed:
                    spawn_task(self.stop(update.chat_id), name=f"call-stop:{update.chat_id}")

    async def boot(self):
        logger.info("Starting PyTgCalls voice engines...")
        self.clients.clear()
        self._next_tasks.clear()
        for index, assistant in enumerate(anony.userbot.clients, 1):
            try:
                client = PyTgCalls(assistant)
                await client.start()
                await self._register(client)
                self.clients.append(client)
                logger.info("PyTgCalls assistant %s started.", index)
            except Exception:
                logger.exception("PyTgCalls assistant %s failed.", index)

        if not self.clients:
            raise SystemExit(
                "No voice call clients are running. Check pyrotgfork==2.2.24 "
                "and py-tgcalls==2.3.3."
            )

    async def shutdown(self):
        for client in list(self.clients):
            try:
                await client.stop()
            except Exception:
                logger.debug("PyTgCalls stop failed", exc_info=True)
        self.clients.clear()
