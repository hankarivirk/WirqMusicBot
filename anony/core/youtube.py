# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


import os
import re
import yt_dlp
import random
import asyncio
import aiohttp
from pathlib import Path

from py_yt import Playlist, Recommendations, VideosSearch

from anony import logger
from anony.helpers import Track, utils


class DummyLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass

class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.cookies = []
        self.checked = False
        self.cookie_dir = "anony/cookies"
        self.warned = False
        # Per-video-id locks so two concurrent requests for the same track
        # can't both pass the "does it exist yet" check and both download.
        self.download_locks: dict[str, asyncio.Lock] = {}
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )
        self.iregex = re.compile(
            r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com|youtu\.be)"
            r"(?!/(watch\?v=[A-Za-z0-9_-]{11}|shorts/[A-Za-z0-9_-]{11}"
            r"|playlist\?list=PL[A-Za-z0-9_-]+|[A-Za-z0-9_-]{11}))\S*"
        )

    def get_cookies(self):
        # Always rescan instead of caching a one-time "checked" flag, so
        # cookies added (or removed) after startup are picked up without
        # requiring a restart. listdir() on a small cookies directory is
        # cheap enough to do on every call.
        try:
            self.cookies = [
                f"{self.cookie_dir}/{file}"
                for file in os.listdir(self.cookie_dir)
                if file.endswith(".txt")
            ]
        except FileNotFoundError:
            self.cookies = []
        self.checked = True
        if not self.cookies:
            if not self.warned:
                self.warned = True
                logger.warning("Cookies are missing; downloads might fail.")
            return None
        self.warned = False
        return random.choice(self.cookies)

    async def save_cookies(self, urls: list[str]) -> None:
        logger.info("Saving cookies from urls...")
        # Drop stale cookie files first so a config change (a fresh set of
        # cookie URLs) can't leave old, possibly-invalid cookies around for
        # get_cookies() to randomly pick.
        try:
            for file in os.listdir(self.cookie_dir):
                if file.endswith(".txt"):
                    os.remove(f"{self.cookie_dir}/{file}")
        except FileNotFoundError:
            os.makedirs(self.cookie_dir, exist_ok=True)

        saved, failed = 0, 0
        async with aiohttp.ClientSession() as session:
            for url in urls:
                name = url.split("/")[-1]
                link = "https://batbin.me/raw/" + name
                try:
                    async with session.get(link) as resp:
                        resp.raise_for_status()
                        data = await resp.read()
                    with open(f"{self.cookie_dir}/{name}.txt", "wb") as fw:
                        fw.write(data)
                    saved += 1
                except Exception as e:
                    # Don't let one bad cookie URL abort the rest of the
                    # batch — log it and keep going.
                    failed += 1
                    logger.warning(f"Failed to save cookie from {link}: {e}")

        self.checked = False  # force a rescan on next get_cookies()
        logger.info(f"Cookies saved in {self.cookie_dir}. ({saved} ok, {failed} failed)")

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    def invalid(self, url: str) -> bool:
        return bool(re.match(self.iregex, url))

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | None:
        try:
            _search = VideosSearch(query, limit=1, with_live=False)
            results = await _search.next()
        except Exception as e:
            logger.warning(f"YouTube search failed for query {query!r}: {e}")
            return None
        if results and results["result"]:
            data = results["result"][0]
            thumbs = data.get("thumbnails") or [{}]
            thumb_url = thumbs[-1].get("url") if thumbs else None
            return Track(
                id=data.get("id"),
                channel_name=data.get("channel", {}).get("name"),
                duration=data.get("duration"),
                duration_sec=utils.to_seconds(data.get("duration")),
                message_id=m_id,
                title=(data.get("title") or data.get("id") or "Unknown")[:25],
                thumbnail=thumb_url.split("?")[0] if thumb_url else None,
                url=data.get("link"),
                view_count=data.get("viewCount", {}).get("short"),
                video=video,
            )
        return None

    async def playlist(
        self, limit: int, user: str, url: str, video: bool
    ) -> tuple[list[Track], str | None]:
        tracks = []
        title = None
        try:
            plist = await Playlist.get(url)
            title = (plist.get("info") or {}).get("title") or plist.get("title")
            for data in plist["videos"][:limit]:
                thumbs = data.get("thumbnails") or [{}]
                thumb_url = thumbs[-1].get("url") if thumbs else None
                link = data.get("link") or self.base
                track = Track(
                    id=data.get("id"),
                    channel_name=data.get("channel", {}).get("name", ""),
                    duration=data.get("duration"),
                    duration_sec=utils.to_seconds(data.get("duration")),
                    title=(data.get("title") or data.get("id") or "Unknown")[:25],
                    thumbnail=thumb_url.split("?")[0] if thumb_url else None,
                    url=link.split("&list=")[0],
                    user=user,
                    view_count="",
                    video=video,
                )
                tracks.append(track)
        except Exception as e:
            logger.warning(f"Failed to process playlist {url!r}: {e}")
        return tracks, title

    async def related(self, video_id: str, exclude: set[str] | None = None) -> Track | None:
        """Fetch a single "up next" track for autoplay — the same data
        YouTube's own watch-next panel is built from — skipping anything
        in `exclude` (already played, or already queued) and live streams.
        """
        exclude = exclude or set()
        try:
            results = await Recommendations.get(video_id)
        except Exception as e:
            logger.warning(f"Failed to fetch autoplay recommendation for {video_id}: {e}")
            return None

        for data in results or []:
            vid = data.get("id")
            if not vid or vid in exclude or data.get("isLive"):
                continue

            thumbs = data.get("thumbnails") or [{}]
            thumb_url = thumbs[-1].get("url") if thumbs else None
            return Track(
                id=vid,
                channel_name=data.get("channel", {}).get("name"),
                duration=data.get("duration") or "00:00",
                duration_sec=utils.to_seconds(data.get("duration")),
                title=(data.get("title") or vid)[:25],
                thumbnail=thumb_url.split("?")[0] if thumb_url else None,
                url=self.base + vid,
                view_count=data.get("viewCount", {}).get("short"),
                video=False,
            )
        return None

    async def download(self, video_id: str, video: bool = False) -> str | None:
        existing = self._find_downloaded(video_id)
        if existing:
            return existing

        # Serialize concurrent download attempts for the same video_id so
        # two callers can't both pass the exists() check above and both
        # kick off a yt-dlp download (a TOCTOU race).
        lock = self.download_locks.setdefault(video_id, asyncio.Lock())
        async with lock:
            try:
                # Re-check now that we hold the lock: another task may
                # have finished downloading this exact file while we
                # were waiting.
                existing = self._find_downloaded(video_id)
                if existing:
                    return existing

                cookie = self.get_cookies()
                base_opts = {
                    "outtmpl": "downloads/%(id)s.%(ext)s",
                    "quiet": True,
                    "noplaylist": True,
                    "geo_bypass": True,
                    "no_warnings": True,
                    "overwrites": False,
                    "logger": DummyLogger(),
                    "nocheckcertificate": True,
                    "cookiefile": cookie,
                    "remote_components": ["ejs:github"],
                }

                if video:
                    # No YouTube Music fallback for video: it only ever serves audio.
                    urls = [self.base + video_id]
                    ydl_opts = {
                        **base_opts,
                        "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio)",
                        "merge_output_format": "mp4",
                    }
                else:
                    # Prefer music.youtube.com: it's an audio-only source, so
                    # yt-dlp skips probing video formats entirely, which means
                    # a faster extraction and a quicker download start. Fall
                    # back to the regular watch page if the track isn't on
                    # YouTube Music (e.g. it's not a music upload).
                    urls = [
                        f"https://music.youtube.com/watch?v={video_id}",
                        self.base + video_id,
                    ]
                    ydl_opts = {
                        **base_opts,
                        "format": "bestaudio[ext=webm][acodec=opus]/bestaudio",
                    }

                def _download():
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        for source in urls:
                            try:
                                ydl.download([source])
                            except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError):
                                continue
                            except Exception as ex:
                                logger.warning("Download failed (%s): %s", source, ex)
                                continue
                            # yt-dlp's actual output extension can differ
                            # from our assumed `ext` depending on what
                            # format was actually available/merged, so
                            # look for whatever file it produced instead
                            # of assuming the fixed filename.
                            found = self._find_downloaded(video_id)
                            if found:
                                return found
                    return None

                return await asyncio.to_thread(_download)
            finally:
                self.download_locks.pop(video_id, None)

    @staticmethod
    def _find_downloaded(video_id: str) -> str | None:
        """Return the path of whatever file yt-dlp actually produced for
        this video_id, regardless of its extension."""
        matches = sorted(Path("downloads").glob(f"{video_id}.*"))
        return str(matches[0]) if matches else None
