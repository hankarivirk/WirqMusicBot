# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


import os
import re
import yt_dlp
import random
import shutil
import asyncio
import aiohttp
from pathlib import Path
from urllib.parse import urlencode

from py_yt import Playlist, Recommendations, VideosSearch
from youtubesearchpython.core.requests import RequestCore
from youtubesearchpython.core.constants import searchKey, userAgent
from youtubesearchpython.core.utils import normalize_thumbnails

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
        # Checked once at startup, not per-download: if aria2c is on this
        # host, yt-dlp can pull a single file over several parallel
        # connections instead of one — same file, same quality, faster
        # wall-clock download. If it's not installed, falls back to
        # yt-dlp's normal built-in downloader with no behavior change.
        self._aria2c_path = shutil.which("aria2c")
        if self._aria2c_path:
            logger.info("aria2c found — downloads will use parallel connections.")
        else:
            logger.info(
                "aria2c not found — downloads will use yt-dlp's single-"
                "connection downloader. Installing aria2c on this host "
                "(e.g. `apt install aria2`) would speed up downloads."
            )
        self.regex = re.compile(
            r"(?:https?://)?(?:www\.|m\.|music\.)?(?:"
            r"youtube\.com/watch\?v=[A-Za-z0-9_-]{11}"
            r"|youtube\.com/shorts/[A-Za-z0-9_-]{11}"
            r"|youtube\.com/playlist\?list=[A-Za-z0-9_-]{2,}"
            r"|youtu\.be/[A-Za-z0-9_-]{11}"
            r")(?:[&?][^\s]*)?"
        )
        self.iregex = re.compile(
            r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com|youtu\.be)"
            r"(?!/(watch\?v=[A-Za-z0-9_-]{11}|shorts/[A-Za-z0-9_-]{11}"
            r"|playlist\?list=[A-Za-z0-9_-]{2,}|[A-Za-z0-9_-]{11}))\S*"
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

    async def search(self, query: str, m_id: int, video: bool = False, music: bool = False) -> Track | None:
        if music and not video:
            # /playmusic — YouTube Music's catalog ONLY, never falls
            # back to regular YouTube search. If it's not on YT Music,
            # /playmusic should say so rather than quietly playing a
            # regular-YouTube result instead (that's what plain /play
            # is for).
            return await self._search_music(query, m_id)
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

    async def _search_music(self, query: str, m_id: int) -> Track | None:
        """Search YouTube Music's own catalog (a different Innertube
        client context than the regular-YouTube search the rest of this
        class uses) so a plain text query resolves to the proper
        studio/official-audio track. Best-effort only: any request
        failure or unrecognized response shape just returns None so
        `search()` falls back to the regular YouTube search."""
        try:
            # Deliberately no `params` filter here: YT Music's internal
            # encoding for "Songs only" isn't something verifiable
            # offline, and a wrong value risks the endpoint rejecting
            # the whole request. A plain query still returns a "Songs"
            # shelf we can pick out below, just alongside other shelves
            # (top result/videos/albums) that we simply skip past.
            body = RequestCore.buildInnertubeBody(
                client={
                    "clientName": "WEB_REMIX",
                    "clientVersion": "1.20241030.01.00",
                    "hl": "en",
                    "gl": "US",
                },
                query=query,
            )
            url = "https://music.youtube.com/youtubei/v1/search?" + urlencode(
                {"key": searchKey, "prettyPrint": "false"}
            )
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=body,
                    headers={
                        "User-Agent": userAgent,
                        "Content-Type": "application/json",
                        "Origin": "https://music.youtube.com",
                        "Referer": "https://music.youtube.com/search",
                        "X-Youtube-Client-Name": "67",
                        "X-Youtube-Client-Version": "1.20241030.01.00",
                    },
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as resp:
                    if resp.status != 200:
                        body_preview = (await resp.text())[:300]
                        logger.warning(
                            f"YouTube Music search HTTP {resp.status} for "
                            f"query {query!r}: {body_preview}"
                        )
                        return None
                    data = await resp.json()
        except Exception as e:
            logger.warning(f"YouTube Music search request failed for query {query!r}: {e}")
            return None

        item = self._first_music_song(data)
        if not item or not item.get("videoId"):
            # Request succeeded but nothing recognizable came back —
            # almost always means YT Music changed its response shape.
            # Logging the top-level keys here (instead of nothing) is
            # what lets this be fixed from a real deployment's logs.
            logger.warning(
                f"YouTube Music search returned no parsable song for "
                f"query {query!r}; top-level keys: {list(data.keys()) if isinstance(data, dict) else type(data)}"
            )
            return None

        vid = item["videoId"]
        thumbs = item.get("thumbnails") or [{}]
        thumb_url = thumbs[-1].get("url") if thumbs else None
        return Track(
            id=vid,
            channel_name=item.get("artist"),
            duration=item.get("duration") or "00:00",
            duration_sec=utils.to_seconds(item.get("duration")),
            message_id=m_id,
            title=(item.get("title") or vid)[:25],
            thumbnail=thumb_url.split("?")[0] if thumb_url else None,
            url=f"https://music.youtube.com/watch?v={vid}",
            view_count=None,
            video=False,
        )

    @staticmethod
    def _first_music_song(data: dict) -> dict | None:
        """Pull the first song entry out of a YouTube Music search
        response. Written defensively (checked against multiple known
        field-name variants) since YT Music's internal schema shifts
        subtly from time to time."""
        try:
            tabs = data["contents"]["tabbedSearchResultsRenderer"]["tabs"]
            contents = tabs[0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"]
        except (KeyError, IndexError, TypeError):
            return None

        # An unfiltered search returns several shelves (Top result,
        # Songs, Videos, Albums, ...). Prefer one explicitly titled
        # "Songs" so we don't accidentally grab a Videos shelf just
        # because it happened to come first; fall back to the first
        # shelf found at all if no title matches (better than nothing).
        shelves = [s.get("musicShelfRenderer") for s in contents if s.get("musicShelfRenderer")]
        songs_shelf = None
        for shelf in shelves:
            title = ""
            try:
                title = shelf["title"]["runs"][0]["text"]
            except (KeyError, IndexError, TypeError):
                pass
            if "song" in title.lower():
                songs_shelf = shelf
                break
        ordered_shelves = ([songs_shelf] if songs_shelf else []) + shelves

        for shelf in ordered_shelves:
            if not shelf:
                continue
            for row in shelf.get("contents") or []:
                renderer = row.get("musicResponsiveListItemRenderer")
                if not renderer:
                    continue

                video_id = (
                    renderer.get("playlistItemData", {}).get("videoId")
                    or renderer.get("overlay", {})
                    .get("musicItemThumbnailOverlayRenderer", {})
                    .get("content", {})
                    .get("musicPlayButtonRenderer", {})
                    .get("playNavigationEndpoint", {})
                    .get("watchEndpoint", {})
                    .get("videoId")
                )
                if not video_id:
                    continue

                flex = renderer.get("flexColumns") or []
                title = YouTube._music_column_text(flex[0]) if flex else None
                artist = None
                duration = None
                if len(flex) > 1:
                    runs = YouTube._music_column_runs(flex[1])
                    if runs:
                        artist = runs[0].get("text")
                        last = (runs[-1].get("text") or "").strip()
                        if re.match(r"^\d{1,2}(:\d{2}){1,2}$", last):
                            duration = last

                if not duration:
                    fixed = renderer.get("fixedColumns") or []
                    if fixed:
                        duration = YouTube._music_column_text(fixed[0])

                thumb_source = (
                    renderer.get("thumbnail", {})
                    .get("musicThumbnailRenderer", {})
                    .get("thumbnail", {})
                    .get("thumbnails")
                )

                return {
                    "videoId": video_id,
                    "title": title,
                    "artist": artist,
                    "duration": duration,
                    "thumbnails": normalize_thumbnails(thumb_source, video_id),
                }
        return None

    @staticmethod
    def _music_column_runs(column: dict) -> list:
        return (
            column.get("musicResponsiveListItemFlexColumnRenderer", {})
            .get("text", {})
            .get("runs")
            or []
        )

    @staticmethod
    def _music_column_text(column: dict) -> str | None:
        renderer = (
            column.get("musicResponsiveListItemFlexColumnRenderer")
            or column.get("musicResponsiveListItemFixedColumnRenderer")
            or {}
        )
        runs = renderer.get("text", {}).get("runs")
        return runs[0].get("text") if runs else None

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
        """Fetch a single "up next" track — kept for any caller that
        just wants one result. See related_batch() for multiple."""
        results = await self.related_batch(video_id, exclude, count=1)
        return results[0] if results else None

    async def related_batch(
        self, video_id: str, exclude: set[str] | None = None, count: int = 3
    ) -> list[Track]:
        """Fetch up to `count` "up next" tracks — the same data
        YouTube's own watch-next panel is built from — skipping
        anything in `exclude` (already played, or already queued) and
        live streams. Used both by autoplay and by the recommendation
        cards (a few candidates to actually choose from, not just one
        picked silently).
        """
        exclude = exclude or set()
        try:
            results = await Recommendations.get(video_id)
        except Exception as e:
            logger.warning(f"Failed to fetch recommendations for {video_id}: {e}")
            return []

        tracks: list[Track] = []
        for data in results or []:
            if len(tracks) >= count:
                break

            vid = data.get("id")
            if not vid or vid in exclude or data.get("isLive"):
                continue

            thumbs = data.get("thumbnails") or [{}]
            thumb_url = thumbs[-1].get("url") if thumbs else None
            channel_name = data.get("channel", {}).get("name")
            duration = data.get("duration")
            duration_sec = utils.to_seconds(duration)
            view_count = data.get("viewCount", {}).get("short")

            # YouTube's watch-next feed sometimes returns entries in a
            # newer "lockup card" format that only carries id/title/
            # thumbnail — no duration, channel, or view count at all.
            # Fill the gaps with a direct, download-free metadata lookup
            # so recommended tracks aren't missing this info in the UI.
            if not duration or not channel_name:
                info = await self._quick_info(vid)
                if info:
                    duration_sec = duration_sec or info["duration_sec"]
                    duration = duration or info["duration"]
                    channel_name = channel_name or info["channel_name"]
                    view_count = view_count or info["view_count"]
                    if not thumb_url:
                        thumb_url = info["thumbnail"]

            tracks.append(Track(
                id=vid,
                channel_name=channel_name,
                duration=duration or "00:00",
                duration_sec=duration_sec,
                title=(data.get("title") or vid)[:25],
                thumbnail=thumb_url.split("?")[0] if thumb_url else None,
                url=self.base + vid,
                view_count=view_count,
                video=False,
            ))
        return tracks

    @staticmethod
    def _format_duration(seconds) -> str:
        seconds = int(seconds or 0)
        if not seconds:
            return "00:00"
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

    async def _quick_info(self, video_id: str) -> dict | None:
        """Metadata-only lookup (no download) used purely as a fallback
        when the watch-next feed's card format omitted duration/channel/
        thumbnail. Kept separate from download() so it never touches the
        downloads/ directory or fetches actual media."""
        def _fetch():
            opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "noplaylist": True,
                "logger": DummyLogger(),
                "cookiefile": self.get_cookies(),
                "cachedir": ".cache/yt-dlp",
                "socket_timeout": 10,
            }
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(self.base + video_id, download=False)
            except Exception as e:
                logger.warning(f"Quick metadata lookup failed for {video_id}: {e}")
                return None

        data = await asyncio.to_thread(_fetch)
        if not data:
            return None
        seconds = data.get("duration") or 0
        return {
            "duration": self._format_duration(seconds),
            "duration_sec": int(seconds),
            "channel_name": data.get("uploader") or data.get("channel"),
            "thumbnail": data.get("thumbnail"),
            "view_count": data.get("view_count"),
        }

    async def get_stream_url(self, video_id: str) -> str | None:
        """Resolve a direct, immediately-playable CDN URL for this
        track WITHOUT downloading anything to disk — a metadata-only
        yt-dlp request, dramatically faster than a full download. Used
        so playback can start right away while the real file is cached
        to disk in the background. Audio only: a muxed video+audio
        direct URL would need an actual download+merge to produce a
        single playable stream, so /vplay still uses the full download."""
        # Already cached locally (e.g. prefetched while the previous
        # track was playing, or played before) — just use that instead
        # of a network round-trip.
        existing = self._find_downloaded(video_id)
        if existing:
            return existing

        cookie = self.get_cookies()
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "logger": DummyLogger(),
            "cookiefile": cookie,
            "format": "bestaudio[ext=webm][acodec=opus]/bestaudio",
            "cachedir": ".cache/yt-dlp",
            "socket_timeout": 10,
        }
        # Same music.youtube.com-first order as download() — most tracks
        # resolve there, which skips YouTube's heavier video-format probing.
        urls = [f"https://music.youtube.com/watch?v={video_id}", self.base + video_id]

        def _resolve():
            with yt_dlp.YoutubeDL(opts) as ydl:
                for source in urls:
                    try:
                        info = ydl.extract_info(source, download=False)
                    except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError):
                        continue
                    except Exception as e:
                        logger.warning(f"Direct stream resolution failed ({source}): {e}")
                        continue
                    if info and info.get("url"):
                        return info["url"]
            return None

        return await asyncio.to_thread(_resolve)

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
                    # Explicit, persistent, writable cache dir — the
                    # "ejs:github" component (and yt-dlp's own extractor
                    # cache) is meant to download once and be reused on
                    # every later request. On some hosts the default
                    # cache location isn't reliably persisted between
                    # requests/restarts, silently turning a one-time
                    # fetch into a per-download one and adding real
                    # latency every single time. Pinning it inside the
                    # project directory guarantees it actually sticks.
                    "cachedir": ".cache/yt-dlp",
                    # Fail fast on a dead/slow source instead of hanging
                    # — matters most for the music.youtube.com attempt,
                    # so a bad connection there doesn't stall the
                    # youtube.com fallback for long.
                    "socket_timeout": 10,
                    # Native yt-dlp speedup for any fragmented/DASH
                    # stream (separate from the aria2c setup below,
                    # which speeds up plain single-file downloads) —
                    # harmless no-op for formats that aren't fragmented.
                    "concurrent_fragment_downloads": 4,
                }
                if self._aria2c_path:
                    base_opts["external_downloader"] = "aria2c"
                    base_opts["external_downloader_args"] = {
                        "aria2c": [
                            "-x", "16",   # up to 16 connections per download
                            "-s", "16",   # split the file into 16 pieces
                            "-k", "1M",   # minimum split size per piece
                        ]
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
                        # Highest-quality audio stream available —
                        # speed comes from parallel connections (see
                        # base_opts' aria2c/concurrent-fragment setup
                        # below), not from settling for a lower bitrate.
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
