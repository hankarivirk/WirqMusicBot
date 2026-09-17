# Copyright (c) 2025 wirq4
# Licensed under the MIT License.
# Optimized and Resilient YouTube Handler for Wirq Music Bot

import os
import re
import random
import shutil
import asyncio
import aiohttp
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import yt_dlp

from youtubesearchpython.core.requests import RequestCore
from youtubesearchpython.core.constants import searchKey, userAgent
from py_yt import VideosSearch
from wirq import logger
from wirq.helpers._dataclass import Track
from wirq.helpers._utilities import utils

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOWNLOAD_DIR = _BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


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
        self.cookies: List[str] = []
        self.cookie_dir = "wirq/cookies"
        self.warned = False
        self.bad_cookies: set[str] = set()
        self.download_locks: Dict[str, asyncio.Lock] = {}

        self._aria2c_path = shutil.which("aria2c")
        if self._aria2c_path:
            logger.info("aria2c detected — optimized chunk downloading enabled.")
        else:
            logger.info("aria2c not found — using native yt-dlp HTTP downloader.")

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

        self._cookie_failure_hints = (
            "sign in",
            "cookies",
            "confirm you're not a bot",
            "bot",
            "the page needs to be reloaded",
            "reload",
            "unplayable",
            "403",
            "forbidden",
            "login",
            "account",
        )

    def get_cookies(self) -> Optional[str]:
        """Fetch a valid cookie file with fallback and refresh."""
        try:
            if os.path.exists(self.cookie_dir):
                self.cookies = [
                    os.path.join(self.cookie_dir, f)
                    for f in os.listdir(self.cookie_dir)
                    if f.endswith(".txt") and os.path.getsize(os.path.join(self.cookie_dir, f)) > 0
                ]
            else:
                self.cookies = []
        except Exception as e:
            logger.warning(f"Error scanning cookie directory: {e}")
            self.cookies = []

        if not self.cookies:
            if not self.warned:
                self.warned = True
                logger.warning("No cookies configured in wirq/cookies. Some restricted downloads may fail.")
            return None

        self.warned = False
        usable = [c for c in self.cookies if c not in self.bad_cookies]
        if not usable:
            self.bad_cookies.clear()
            usable = self.cookies

        return random.choice(usable) if usable else None

    def mark_cookie_bad(self, cookie: Optional[str]) -> None:
        if cookie:
            logger.warning(f"Marking cookie temporarily invalid: {cookie}")
            self.bad_cookies.add(cookie)
            self.bad_cookies.add(os.path.abspath(cookie))
            self.bad_cookies.add(os.path.basename(cookie))

    async def save_cookies(self, urls: List[str]) -> None:
        """Download cookies from specified URLs into the cookies directory."""
        self.bad_cookies.clear()
        os.makedirs(self.cookie_dir, exist_ok=True)

        for f in os.listdir(self.cookie_dir):
            if f.endswith(".txt"):
                try:
                    os.remove(os.path.join(self.cookie_dir, f))
                except Exception:
                    pass

        saved, failed = 0, 0
        async with aiohttp.ClientSession() as session:
            for url in urls:
                name = url.split("/")[-1]
                link = f"https://batbin.me/raw/{name}" if "batbin.me" in url else url
                try:
                    async with session.get(link, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            # Check basic validity
                            decoded = data.decode("utf-8", errors="ignore")
                            if "youtube.com" in decoded or "# Netscape" in decoded:
                                with open(os.path.join(self.cookie_dir, f"{name}.txt"), "wb") as fw:
                                    fw.write(data)
                                saved += 1
                            else:
                                logger.warning(f"Cookie from {link} failed format check (not a Netscape YouTube cookie).")
                                failed += 1
                        else:
                            failed += 1
                except Exception as e:
                    failed += 1
                    logger.warning(f"Failed to fetch cookie from {link}: {e}")

        logger.info(f"Cookies updated: {saved} succeeded, {failed} failed.")

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    def invalid(self, url: str) -> bool:
        return bool(re.match(self.iregex, url))

    async def search(self, query: str, m_id: int, video: bool = False, music: bool = False) -> Optional[Track]:
        """Search YouTube tracks with direct URL fast-path handling."""
        # 1. Direct YouTube link detection
        match = re.search(r"(?:v=|\/|youtu\.be\/|embed\/|shorts\/)([0-9A-Za-z_-]{11})", query)
        if match:
            vid = match.group(1)
            info = await self.get_info(vid)
            if info:
                title = (info.get("title") or "YouTube Track")[:50]
                channel = info.get("channel") or info.get("uploader") or "YouTube"
                duration = info.get("duration_string") or "00:00"
                dur_sec = int(info.get("duration") or 0)
                thumb_url = info.get("thumbnail") or f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
                return Track(
                    id=vid,
                    channel_name=channel,
                    duration=duration,
                    duration_sec=dur_sec,
                    message_id=m_id,
                    title=title,
                    thumbnail=thumb_url.split("?")[0] if thumb_url else None,
                    url=f"https://www.youtube.com/watch?v={vid}",
                    view_count=str(info.get("view_count") or ""),
                    video=video,
                )
            return Track(
                id=vid,
                channel_name="YouTube",
                duration="00:00",
                duration_sec=0,
                message_id=m_id,
                title="YouTube Track",
                thumbnail=f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
                url=f"https://www.youtube.com/watch?v={vid}",
                view_count="",
                video=video,
            )

        # 2. Text keyword search via VideosSearch
        try:
            _search = VideosSearch(query, limit=1, with_live=False)
            results = await _search.next()
            if results and results.get("result"):
                data = results["result"][0]
                thumbs = data.get("thumbnails") or [{}]
                thumb_url = thumbs[-1].get("url") if thumbs else None
                return Track(
                    id=data.get("id"),
                    channel_name=data.get("channel", {}).get("name"),
                    duration=data.get("duration"),
                    duration_sec=utils.to_seconds(data.get("duration")),
                    message_id=m_id,
                    title=(data.get("title") or data.get("id") or "Unknown")[:50],
                    thumbnail=thumb_url.split("?")[0] if thumb_url else None,
                    url=data.get("link"),
                    view_count=data.get("viewCount", {}).get("short"),
                    video=video,
                )
        except Exception as e:
            logger.warning(f"YouTube search error for {query!r}: {e}")
        return None

    async def get_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Quick metadata extraction without downloading media."""
        url = self.base + video_id
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "logger": DummyLogger(),
            "socket_timeout": 10,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "ios", "default", "-tv_downgraded"]
                }
            },
        }

        def _fetch():
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(url, download=False)
            except Exception:
                return None

        return await asyncio.to_thread(_fetch)

    async def playlist(self, url: str, limit: int = 50) -> List[Track]:
        """Extract tracks from a YouTube playlist."""
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "skip_download": True,
            "logger": DummyLogger(),
            "socket_timeout": 12,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "ios", "default", "-tv_downgraded"]
                }
            },
        }

        def _extract():
            tracks = []
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info and "entries" in info:
                        for entry in info["entries"][:limit]:
                            if not entry:
                                continue
                            vid = entry.get("id")
                            if not vid:
                                continue
                            tracks.append(
                                Track(
                                    id=vid,
                                    channel_name=entry.get("uploader") or "YouTube",
                                    duration=entry.get("duration_string") or "00:00",
                                    duration_sec=int(entry.get("duration") or 0),
                                    message_id=0,
                                    title=(entry.get("title") or "Track")[:50],
                                    thumbnail=entry.get("thumbnail") or f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
                                    url=f"https://www.youtube.com/watch?v={vid}",
                                    view_count="",
                                    video=False,
                                )
                            )
            except Exception as e:
                logger.warning(f"Playlist extraction error: {e}")
            return tracks

        return await asyncio.to_thread(_extract)

    async def related(self, video_id: str, exclude: Optional[set[str]] = None) -> Optional[Track]:
        """Fetch next recommended track for autoplay."""
        exclude = exclude or set()
        try:
            from py_yt import Recommendations
            results = await Recommendations.get(video_id)
            if results:
                for data in results:
                    vid = data.get("id")
                    if vid and vid not in exclude and not data.get("isLive"):
                        thumbs = data.get("thumbnails") or [{}]
                        thumb_url = thumbs[-1].get("url") if thumbs else None
                        return Track(
                            id=vid,
                            channel_name=data.get("channel", {}).get("name", "YouTube"),
                            duration=data.get("duration") or "00:00",
                            duration_sec=utils.to_seconds(data.get("duration")),
                            message_id=0,
                            title=(data.get("title") or "YouTube Track")[:50],
                            thumbnail=thumb_url.split("?")[0] if thumb_url else None,
                            url=f"https://www.youtube.com/watch?v={vid}",
                            view_count="",
                            video=False,
                        )
        except Exception as e:
            logger.warning(f"Failed to fetch autoplay recommendations: {e}")
        return None

    def _get_base_opts(
        self,
        cookie: Optional[str] = None,
        player_clients: Optional[List[str]] = None,
        use_aria2: bool = True,
    ) -> Dict[str, Any]:
        """Optimized yt-dlp base options eliminating 'The page needs to be reloaded'."""
        if player_clients is None:
            # Android and iOS clients bypass web client reload challenges completely
            player_clients = ["android", "ios", "web_embedded"]

        opts: Dict[str, Any] = {
            "outtmpl": f"{DOWNLOAD_DIR}/%(id)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "geo_bypass": True,
            "no_warnings": True,
            "overwrites": False,
            "logger": DummyLogger(),
            "nocheckcertificate": True,
            "cachedir": ".cache/yt-dlp",
            "socket_timeout": 15,
            "retries": 3,
            "fragment_retries": 3,
            "extractor_args": {
                "youtube": {
                    "player_client": player_clients,
                }
            },
        }

        if cookie and os.path.exists(cookie):
            opts["cookiefile"] = cookie

        if use_aria2 and self._aria2c_path:
            opts["external_downloader"] = "aria2c"
            opts["external_downloader_args"] = {
                "aria2c": ["-x", "4", "-s", "4", "-k", "1M", "--check-certificate=false", "--quiet=true"]
            }
        else:
            opts["concurrent_fragment_downloads"] = 4

        return opts

    async def get_stream_url(self, video_id: str) -> Optional[Tuple[str, Dict[str, str]]]:
        """Extract direct audio stream URL with required HTTP headers."""
        url = self.base + video_id
        cookie = self.get_cookies()
        opts = {
            **self._get_base_opts(cookie),
            "format": "bestaudio[ext=webm][acodec=opus]/bestaudio/best",
            "skip_download": True,
        }

        def _extract():
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if not info:
                        return None
                    stream_url = info.get("url")
                    headers = info.get("http_headers") or {}
                    if stream_url:
                        return stream_url, headers
            except Exception as e:
                logger.warning(f"Stream URL extraction failed for {video_id}: {e}")
            return None

        return await asyncio.to_thread(_extract)

    async def download(self, video_id: str, video: bool = False) -> Optional[str]:
        """Resilient multi-tier download that automatically bypasses 'page needs to be reloaded',
        cookie corruption, YouTube 403 CDN blocks, and player client limitations."""
        existing = self._find_downloaded(video_id)
        if existing:
            return existing

        lock = self.download_locks.setdefault(video_id, asyncio.Lock())
        async with lock:
            existing = self._find_downloaded(video_id)
            if existing:
                return existing

            target_url = self.base + video_id
            cookie = self.get_cookies()

            if video:
                fmt = "bestvideo[height<=?720][width<=?1280][ext=mp4]+bestaudio[ext=m4a]/best[height<=?720]"
            else:
                fmt = "bestaudio[ext=webm][acodec=opus]/bestaudio/best"

            # Multi-tier fallback strategy:
            # 1. Primary: Mobile & Web clients with cookie (excluding -tv_downgraded)
            # 2. Fallback 1: Pure Android/iOS mobile client (immune to web reload errors)
            # 3. Fallback 2: Clean Anonymous request WITHOUT cookies (fixes bad/expired cookie lockout)
            # 4. Fallback 3: Native HTTP downloader without aria2c (bypasses CDN 403 blocks)
            # Optimized player client strategies:
            # 1. Primary: Android, iOS, and Web-embedded clients with cookie (bypasses tv_downgraded reload bug)
            # 2. Fallback 1: Pure Android/iOS mobile clients without cookies (immune to account/cookie reload challenge)
            # 3. Fallback 2: Native HTTP downloader without aria2c (bypasses CDN connection limits and 403 blocks)
            # Ultra-resilient download strategies:
            # 1. Mobile clients without cookies: completely eliminates 'The page needs to be reloaded' for all standard music
            # 2. Web embedded client (clean anonymous)
            # 3. Cookie-authenticated fallback: only needed for age-restricted / members-only videos
            # 4. Aria2 multi-connection fallback
            strategies = [
                {"use_cookie": False, "clients": ["android", "ios"], "aria2": False, "desc": "mobile clean client (android/ios)"},
                {"use_cookie": False, "clients": ["web_embedded"], "aria2": False, "desc": "web_embedded clean"},
                {"use_cookie": True, "clients": ["android", "ios", "web_embedded"], "aria2": False, "desc": "authenticated (cookie)"},
                {"use_cookie": False, "clients": ["android", "ios"], "aria2": True, "desc": "aria2 multi-connection"},
            ]

            def _try_download():
                for strat in strategies:
                    c_file = cookie if strat["use_cookie"] and cookie not in self.bad_cookies else None
                    opts = self._get_base_opts(
                        cookie=c_file,
                        player_clients=strat["clients"],
                        use_aria2=strat["aria2"]
                    )
                    opts["format"] = fmt
                    if video:
                        opts["merge_output_format"] = "mp4"

                    try:
                        with yt_dlp.YoutubeDL(opts) as ydl:
                            ydl.download([target_url])
                        found = self._find_downloaded(video_id)
                        if found:
                            logger.info(f"Successfully downloaded {video_id} using {strat['desc']}.")
                            return found
                    except Exception as ex:
                        err_str = str(ex).lower()
                        logger.warning(f"Download attempt failed for {video_id} ({strat['desc']}): {ex}")
                        if c_file and any(hint in err_str for hint in self._cookie_failure_hints):
                            self.mark_cookie_bad(c_file)
                            c_file = None

                return self._find_downloaded(video_id)

            return await asyncio.to_thread(_try_download)

    @classmethod
    def _find_downloaded(cls, video_id: str) -> Optional[str]:
        """Find downloaded file matching video_id in the downloads folder."""
        common_exts = [".webm", ".mp4", ".m4a", ".mp3", ".opus", ".mkv", ".ogg"]
        for search_dir in [DOWNLOAD_DIR, Path("downloads")]:
            # Direct extension check
            for ext in common_exts:
                target = search_dir / f"{video_id}{ext}"
                if target.exists():
                    return str(target)
            # Glob fallback
            if search_dir.exists():
                try:
                    matches = list(search_dir.glob(f"{video_id}.*"))
                    if matches:
                        return str(matches[0])
                except Exception:
                    pass
        return None
