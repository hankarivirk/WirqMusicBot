# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


import time
import asyncio
import os

from pyrogram import enums, errors, filters, types

from anony import anon, app, config, db, lang, logger, queue, tasks, userbot, yt, spawn_task
from anony.helpers import buttons, utils


@app.on_message(filters.video_chat_started, group=19)
@app.on_message(filters.video_chat_ended, group=20)
async def _watcher_vc(_, m: types.Message):
    await anon.stop(m.chat.id)


async def auto_leave():
    # Tracks consecutive hourly checks a chat has shown no active call.
    # Persists across loop iterations (this function IS the loop), so a
    # chat only actually gets left after AUTO_LEAVE_GRACE consecutive
    # idle checks in a row — not the very first time it happens to have
    # no call running, which is what made this aggressive before (a
    # chat that uses the bot for a few minutes every couple hours would
    # get kicked between uses).
    idle_streak: dict[int, int] = {}
    while True:
        await asyncio.sleep(3600)
        for ub in userbot.clients:
            try:
                # Evaluate every group/supergroup dialog, not just the
                # last 20 — capping the list here meant chats outside that
                # window were never considered for auto-leave at all.
                chats = [dialog.chat.id async for dialog in ub.get_dialogs()
                            if dialog.chat.type in [
                                enums.ChatType.GROUP, enums.ChatType.SUPERGROUP,
                            ]]
                seen = set(chats)
                for chat in chats:
                    if chat == app.logger or chat in config.AUTO_LEAVE_EXCLUDE:
                        continue
                    if chat in db.active_calls:
                        idle_streak.pop(chat, None)
                        continue

                    idle_streak[chat] = idle_streak.get(chat, 0) + 1
                    if idle_streak[chat] < config.AUTO_LEAVE_GRACE:
                        continue

                    await ub.leave_chat(chat)
                    idle_streak.pop(chat, None)
                    await asyncio.sleep(12)

                # Drop tracking for chats this assistant is no longer
                # even in (left through some other path), so the dict
                # doesn't grow unbounded over a long-running process.
                for chat in list(idle_streak):
                    if chat not in seen:
                        idle_streak.pop(chat, None)
            except asyncio.CancelledError:
                raise
            except Exception:
                continue


async def track_time():
    while True:
        await asyncio.sleep(1)
        try:
            for chat_id in list(db.active_calls):
                if not await db.playing(chat_id):
                    continue

                media = queue.get_current(chat_id)
                if not media:
                    continue
                media.time += 1
        except asyncio.CancelledError:
            raise
        except Exception as e:
            # Any other exception here used to bubble out of the `while
            # True` loop entirely, permanently killing this background
            # task with no restart. Log it and keep the loop alive instead.
            logger.warning(f"track_time() iteration failed: {e}")


async def update_timer(length=10, sleep=12):
    # Tracks an in-flight prefetch task per track id, so this fallback
    # (mirroring calls.py's _cache_and_prefetch, which normally already
    # handles this) doesn't spawn a duplicate download task on every
    # 12-second tick while remaining <= 30 for the same still-downloading
    # track.
    prefetching: set[str] = set()
    while True:
        await asyncio.sleep(sleep)
        for chat_id in list(db.active_calls):
            if not await db.playing(chat_id):
                continue
            try:
                media = queue.get_current(chat_id)
                if not media:
                    continue
                duration, message_id = media.duration_sec, media.message_id
                if not duration or not message_id or not media.time:
                    continue
                played = media.time
                remaining = max(duration - played, 0)
                pos = min(int((played / duration) * length), length - 1)
                timer = "—" * pos + "◉" + "—" * (length - pos - 1)

                if remaining <= 30:
                    next = queue.get_next(chat_id, check=True)
                    if next and not next.file_path and next.id not in prefetching:
                        # Fired as its own task, not awaited inline —
                        # awaiting here blocked this loop's progress
                        # through every OTHER chat in active_calls for
                        # as long as this one download took, so one
                        # slow/stuck download delayed every other
                        # chat's progress-bar update, not just its own.
                        prefetching.add(next.id)

                        async def _prefetch(track=next):
                            try:
                                track.file_path = await yt.download(track.id, video=track.video)
                            except Exception:
                                pass
                            finally:
                                prefetching.discard(track.id)

                        spawn_task(_prefetch(), name=f"timer-prefetch:{next.id}")

                if remaining < 10:
                    remove = True
                else:
                    if config.THUMB_GEN:
                        timer = f"{utils.format_duration(played)} | {timer} | -{utils.format_duration(remaining)}"
                    else:
                        timer = None
                    remove = False

                if not timer and not remove:
                    continue

                await app.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=buttons.controls(
                        chat_id=chat_id, timer=timer, remove=remove
                    ),
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                pass


async def vc_watcher(sleep=15):
    while True:
        await asyncio.sleep(sleep)
        for chat_id in list(db.active_calls):
            try:
                client = await db.get_assistant(chat_id)
                media = queue.get_current(chat_id)
                if not media:
                    continue
                participants = await client.get_participants(chat_id)
                if len(participants) < 2 and media.time > 30:
                    _lang = await lang.get_lang(chat_id)
                    try:
                        sent = await app.edit_message_reply_markup(
                            chat_id=chat_id,
                            message_id=media.message_id,
                            reply_markup=buttons.controls(
                                chat_id=chat_id, status=_lang["stopped"], remove=True
                            ),
                        )
                        await anon.stop(chat_id)
                        await sent.reply_text(_lang["auto_left"])
                    except errors.MessageIdInvalid:
                        pass
            except asyncio.CancelledError:
                raise
            except Exception as e:
                # get_assistant()/get_participants() (and anything else
                # per-chat) used to be unprotected, so one API hiccup for
                # a single chat could crash the whole watcher loop and
                # silently kill this task forever. Log and move on to the
                # next chat instead.
                logger.warning(f"vc_watcher() failed for chat {chat_id}: {e}")


async def cleanup_files():
    """downloads/ (full audio files) and cache/ (generated thumbnails)
    otherwise only get cleared on an explicit /restart — during normal
    long-running operation nothing else ever removes them, so disk
    usage grows until it fills up and downloads/thumbnail generation
    start failing outright. Age-threshold based (not an in-flight
    check against download_locks/active): CLEANUP_MAX_AGE defaults to
    6 hours, comfortably longer than any realistic single download or
    thumbnail render, so an in-progress file is never at risk."""
    while True:
        await asyncio.sleep(config.CLEANUP_INTERVAL)
        cutoff = time.time() - config.CLEANUP_MAX_AGE
        for directory in ("downloads", "cache"):
            try:
                for name in os.listdir(directory):
                    path = os.path.join(directory, name)
                    try:
                        if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                            os.remove(path)
                    except OSError:
                        continue
            except asyncio.CancelledError:
                raise
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.warning(f"cleanup_files() failed for {directory}: {e}")


async def start_background_tasks() -> None:
    """Start long-lived maintenance workers after all services are ready."""
    if config.AUTO_END:
        spawn_task(vc_watcher(), name="vc_watcher")
    if config.AUTO_LEAVE:
        spawn_task(auto_leave(), name="auto_leave")
    spawn_task(track_time(), name="track_time")
    spawn_task(cleanup_files(), name="cleanup_files")
    spawn_task(update_timer(), name="update_timer")
