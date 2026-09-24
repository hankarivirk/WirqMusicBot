import asyncio
import logging
import time
import uuid
from typing import Dict, Any, Optional, List
try:
    from pytgcalls import PyTgCalls
    try:
        from pytgcalls.types import AudioPiped
    except ImportError:
        from pytgcalls.types.input_stream import AudioPiped
except ImportError:
    PyTgCalls = None
    AudioPiped = None
from anony import app
from anony.core.userbot import userbot
from anony.core.youtube import YouTube
from anony.helpers._inline import stream_markup, recommendation_markup
from anony.helpers._queue import Queues
from anony.helpers._play import get_stream_url
from anony.utils.database import is_autoplay, should_show_youtube_thumbnail, get_loop, set_loop

LOGGER = logging.getLogger("MusicFlow.Calls")

class RecommendationSession:
    """Secure, bound recommendation session preventing cross-chat tampering and stale calls."""
    def __init__(self, session_id: str, chat_id: int, base_vid: str, recs: List[Dict[str, Any]], ttl: int = 600):
        self.session_id = session_id
        self.chat_id = chat_id
        self.base_vid = base_vid
        self.recs = recs
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl
        self.offset = 0

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

# Memory store for active recommendation sessions: session_id -> RecommendationSession
REC_SESSIONS: Dict[str, RecommendationSession] = {}

class CallManager:
    def __init__(self):
        self.call = PyTgCalls(userbot.one) if (PyTgCalls and userbot.one) else None
        self.active_tracks: Dict[int, Dict[str, Any]] = {}
        self.recently_played: Dict[int, List[str]] = {}
        self.is_running: bool = False
        if self.call:
            self._register_handlers()

    def _register_handlers(self):
        if not self.call:
            return
        if hasattr(self.call, "on_stream_end"):
            @self.call.on_stream_end()
            async def _stream_end_handler(client, update):
                chat_id = getattr(update, "chat_id", None)
                if chat_id:
                    await self.on_song_end(chat_id)

        if hasattr(self.call, "on_kicked"):
            @self.call.on_kicked()
            async def _kicked_handler(client, chat_id):
                self.active_tracks.pop(chat_id, None)
                Queues.clear_queue(chat_id)

        if hasattr(self.call, "on_closed_voice_chat"):
            @self.call.on_closed_voice_chat()
            async def _closed_handler(client, chat_id):
                self.active_tracks.pop(chat_id, None)
                Queues.clear_queue(chat_id)

    async def start(self):
        self.is_running = False
        if self.call:
            try:
                await self.call.start()
                self.is_running = True
                LOGGER.info("[MUSIC FLOW] PyTgCalls client started.")
            except Exception as e:
                self.is_running = False
                LOGGER.error(f"[MUSIC FLOW] PyTgCalls start failed: {e}")
        else:
            self.is_running = False
            LOGGER.warning("[MUSIC FLOW] PyTgCalls client not initialized.")

    def _record_history(self, chat_id: int, track: Dict[str, Any]):
        hist = self.recently_played.setdefault(chat_id, [])
        vid_id = track.get("video_id") or track.get("id")
        if vid_id:
            hist.append(vid_id)
            if len(hist) > 25:
                hist.pop(0)

    async def play(self, chat_id: int, track: Dict[str, Any]) -> bool:
        """
        Starts streaming audio in voice chat for chat_id.
        CRITICAL: active_tracks is committed ONLY after playback definitely succeeds!
        """
        raw_url = track.get("link") or track.get("url")
        if not track.get("stream_url"):
            track["stream_url"] = await get_stream_url(raw_url)
        
        if not track.get("stream_url"):
            LOGGER.error(f"No stream URL could be resolved for {track.get('title')}")
            return False

        if not self.call:
            LOGGER.error("Voice client is not initialized.")
            return False

        stream = AudioPiped(track["stream_url"])
        playback_ok = False

        try:
            await self.call.join_group_call(chat_id, stream)
            playback_ok = True
        except Exception:
            try:
                await self.call.change_stream(chat_id, stream)
                playback_ok = True
            except Exception as e:
                LOGGER.error(f"Failed to start stream in {chat_id}: {e}")
                playback_ok = False

        if playback_ok:
            # Commit active track ONLY after confirmed playback success
            self.active_tracks[chat_id] = track
            self._record_history(chat_id, track)
            return True
        else:
            # Clear or retain previous state cleanly
            self.active_tracks.pop(chat_id, None)
            return False

    async def pause(self, chat_id: int) -> bool:
        if not self.call or chat_id not in self.active_tracks:
            return False
        try:
            await self.call.pause_stream(chat_id)
            return True
        except Exception as e:
            LOGGER.error(f"Pause error in {chat_id}: {e}")
            return False

    async def resume(self, chat_id: int) -> bool:
        if not self.call or chat_id not in self.active_tracks:
            return False
        try:
            await self.call.resume_stream(chat_id)
            return True
        except Exception as e:
            LOGGER.error(f"Resume error in {chat_id}: {e}")
            return False

    async def stop(self, chat_id: int) -> bool:
        if not self.call:
            return False
        try:
            await self.call.leave_group_call(chat_id)
        except Exception:
            pass
        self.active_tracks.pop(chat_id, None)
        Queues.clear_queue(chat_id)
        return True

    async def seek(self, chat_id: int, seconds: int) -> bool:
        """Seeks the active audio stream to a given position using ffmpeg offset."""
        if not self.call or chat_id not in self.active_tracks or AudioPiped is None:
            return False
        track = self.active_tracks[chat_id]
        stream_url = track.get("stream_url")
        if not stream_url:
            raw_url = track.get("link") or track.get("url")
            stream_url = await get_stream_url(raw_url)
            track["stream_url"] = stream_url

        if not stream_url:
            LOGGER.error(f"Cannot seek: no stream URL for {track.get('title')}")
            return False

        try:
            stream = AudioPiped(stream_url, additional_ffmpeg_parameters=f"-ss {seconds}")
            await self.call.change_stream(chat_id, stream)
            return True
        except Exception as e:
            LOGGER.error(f"Seek failed in {chat_id}: {e}")
            return False

    async def on_song_end(self, chat_id: int):
        """Called automatically when PyTgCalls stream finishes or on skip."""
        # Save reference to current track / last played video ID before any queue operations
        current = self.active_tracks.get(chat_id)
        last_vid = (current.get("video_id") or current.get("id")) if current else None
        if not last_vid and chat_id in self.recently_played and self.recently_played[chat_id]:
            last_vid = self.recently_played[chat_id][-1]

        # 1. Loop Check
        loop_count = await get_loop(chat_id)
        if loop_count > 0 and current:
            await set_loop(chat_id, loop_count - 1)
            try:
                success = await self.play(chat_id, current)
                if success:
                    return
                LOGGER.warning(f"Failed to replay looped track in {chat_id}. Proceeding to queue.")
            except Exception as e:
                LOGGER.error(f"Exception while looping track in {chat_id}: {e}", exc_info=True)

        # 2. Queue Check: Attempt queued tracks in order; skip failed items and continue
        while True:
            next_track = Queues.pop_queue(chat_id)
            if not next_track:
                break
            try:
                success = await self.play(chat_id, next_track)
                if success:
                    await self._send_now_playing(chat_id, next_track)
                    return
                LOGGER.warning(
                    f"Playback failed for queued track '{next_track.get('title', 'Unknown')}' in {chat_id}. Trying next queued track..."
                )
            except Exception as e:
                LOGGER.error(
                    f"Exception playing queued track '{next_track.get('title', 'Unknown')}' in {chat_id}: {e}",
                    exc_info=True
                )

        # 3. Queue Finished -> Handle Autoplay / Recommendations
        # Clear active track as playback of queue has finished
        self.active_tracks.pop(chat_id, None)

        if not last_vid:
            return

        autoplay_active = await is_autoplay(chat_id)
        try:
            recs = await YouTube.get_recommendations(last_vid, limit=12)
        except Exception as e:
            LOGGER.error(f"Error fetching recommendations for {last_vid}: {e}", exc_info=True)
            recs = []

        # Filter out current and recently played tracks
        hist = set(self.recently_played.get(chat_id, []))
        hist.add(last_vid)
        valid_recs = [r for r in recs if (r.get("video_id") or r.get("id")) not in hist]
        if not valid_recs and recs:
            valid_recs = [r for r in recs if (r.get("video_id") or r.get("id")) != last_vid]

        if autoplay_active and valid_recs:
            for auto_track in valid_recs:
                auto_track["requester"] = "Autoplay"
                try:
                    success = await self.play(chat_id, auto_track)
                    if success:
                        await self._send_now_playing(chat_id, auto_track)
                        return
                    LOGGER.warning(f"Failed to play autoplay track '{auto_track.get('title')}' in {chat_id}, trying next recommendation...")
                except Exception as e:
                    LOGGER.error(f"Exception playing autoplay track '{auto_track.get('title')}': {e}", exc_info=True)

            self.active_tracks.pop(chat_id, None)
            await app.send_message(chat_id=chat_id, text="No recommendations right now.")
        elif not autoplay_active and valid_recs:
            # Autoplay OFF -> Create secure recommendation session
            sess_id = uuid.uuid4().hex[:8]
            session = RecommendationSession(sess_id, chat_id, last_vid, valid_recs)
            REC_SESSIONS[sess_id] = session

            markup = recommendation_markup(valid_recs, sess_id, offset=0)
            rec_lines = ["You might like these.", ""]
            for idx, r in enumerate(valid_recs[:4], start=1):
                t_title = r.get("title", "Song")
                t_artist = r.get("channel") or r.get("channel_name") or ""
                rec_lines.append(f"{idx:02d} {t_title} — {t_artist}" if t_artist else f"{idx:02d} {t_title}")
            text = "\n".join(rec_lines)
            await app.send_message(chat_id=chat_id, text=text, reply_markup=markup)
        else:
            await app.send_message(chat_id=chat_id, text="No recommendations right now.")

    async def _send_now_playing(self, chat_id: int, track: Dict[str, Any]):
        """Dispatches Now Playing card respecting thumbnail central policy."""
        title = track.get("title", "Unknown Title")
        url = track.get("url") or track.get("link") or ""
        duration = track.get("duration") or "Unknown"
        channel = track.get("channel") or track.get("channel_name") or "YouTube"
        requester = track.get("requester") or track.get("user") or "Anonymous"

        artist = channel
        text = (
            "Now playing\n\n"
            f"{title}\n"
            f"{artist}\n\n"
            f"Requested by {requester}\n"
            f"Duration: {duration}"
        )
        markup = stream_markup(chat_id)

        show_thumb = await should_show_youtube_thumbnail(chat_id)
        thumb_url = track.get("thumbnail") or track.get("thumb")

        if show_thumb and thumb_url:
            try:
                await app.send_photo(chat_id=chat_id, photo=thumb_url, caption=text, reply_markup=markup)
                return
            except Exception as e:
                LOGGER.warning(f"Failed to send thumbnail photo: {e}")

        await app.send_message(chat_id=chat_id, text=text, reply_markup=markup)

MusicCall = CallManager()
