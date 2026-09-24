import asyncio
import logging
import re
from typing import Dict, List, Optional, Tuple, Any

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

LOGGER = logging.getLogger("MusicFlow.YouTube")

# Gracefully import youtubesearchpython.future if installed
try:
    from youtubesearchpython.future import (
        VideosSearch,
        Playlist,
        Video,
        Recommendations,
    )
    HAS_YT_SEARCH = True
except ImportError:
    HAS_YT_SEARCH = False
    LOGGER.warning("yt-search-python not installed in runtime environment; using yt_dlp fallback.")

def is_youtube_url(url: str) -> bool:
    """Checks whether a given string is a valid YouTube URL."""
    if not url or not isinstance(url, str):
        return False
    patterns = [
        r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+",
        r"(https?://)?(www\.)?youtube\.com/shorts/.+",
        r"(https?://)?(www\.)?youtube\.com/playlist\?list=.+",
    ]
    return any(re.match(p, url.strip()) for p in patterns)

def resolve_playlist_url(url: str) -> bool:
    """Checks whether a given string is a playlist or user mix URL."""
    if not url or not isinstance(url, str):
        return False
    return "list=" in url or "playlist" in url

def resolve_video_url(url_or_id: str) -> str:
    """Converts a video ID or URL into a canonical watch URL."""
    if not url_or_id:
        return ""
    if url_or_id.startswith("http://") or url_or_id.startswith("https://"):
        return url_or_id.strip()
    return f"https://www.youtube.com/watch?v={url_or_id.strip()}"

def _parse_duration_to_sec(dur_str: str) -> int:
    """Parses duration string 'HH:MM:SS' or 'MM:SS' into integer seconds."""
    if not dur_str or dur_str == "Unknown":
        return 0
    try:
        parts = [int(p) for p in dur_str.strip().split(":")]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 1:
            return parts[0]
    except Exception:
        pass
    return 0

def _format_sec_to_dur(seconds: int) -> str:
    """Formats integer seconds into 'MM:SS' or 'HH:MM:SS'."""
    if not seconds or seconds <= 0:
        return "Unknown"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

class YouTubeService:
    """
    MUSIC FLOW YouTube Service Layer.
    Translates raw YouTube data into stable normalized internal representations.
    """
    def __init__(self):
        self.base_watch = "https://www.youtube.com/watch?v="

    def normalize_track(
        self,
        raw: Dict[str, Any],
        requester: str = "Anonymous",
        message_id: Optional[int] = None,
        is_video: bool = False
    ) -> Dict[str, Any]:
        """
        Normalizes any YouTube item into a stable MUSIC FLOW Track object.
        Preserves full title, channel information, and URL-based thumbnails.
        Never invents metadata (Unknown / 0 when missing).
        """
        vid_id = raw.get("id") or raw.get("video_id") or ""
        title = raw.get("title") or "Unknown Title"
        url = raw.get("link") or raw.get("url") or (f"{self.base_watch}{vid_id}" if vid_id else "")
        
        # Duration normalization (Never invent fake 03:00)
        duration = raw.get("duration")
        duration_sec = raw.get("duration_seconds") or raw.get("duration_sec")
        if duration and not duration_sec:
            duration_sec = _parse_duration_to_sec(str(duration))
        elif duration_sec and not duration:
            duration = _format_sec_to_dur(int(duration_sec))
        elif not duration and not duration_sec:
            duration = "Unknown"
            duration_sec = 0

        # Channel normalization
        channel_data = raw.get("channel") or {}
        if isinstance(channel_data, dict):
            channel_name = channel_data.get("name") or raw.get("channel_name") or "YouTube"
            channel_url = channel_data.get("link") or raw.get("channel_url") or ""
        else:
            channel_name = str(channel_data) or "YouTube"
            channel_url = raw.get("channel_url") or ""

        # Thumbnail normalization (URL only, no local files)
        thumbnail = raw.get("thumbnail") or raw.get("thumb")
        if not thumbnail:
            thumbs = raw.get("thumbnails")
            if isinstance(thumbs, list) and thumbs:
                thumbnail = thumbs[-1].get("url") if isinstance(thumbs[-1], dict) else None

        # View count & publish date
        view_count_raw = raw.get("viewCount")
        if isinstance(view_count_raw, dict):
            view_count = view_count_raw.get("short") or view_count_raw.get("text") or "N/A"
        elif isinstance(view_count_raw, (int, str)):
            view_count = str(view_count_raw)
        else:
            view_count = raw.get("views") or "N/A"

        published = raw.get("publishedTime") or raw.get("published") or "N/A"

        return {
            "video_id": str(vid_id),
            "id": str(vid_id),
            "title": str(title),
            "url": str(url),
            "link": str(url),
            "duration": str(duration),
            "duration_seconds": int(duration_sec),
            "duration_sec": int(duration_sec),
            "channel": str(channel_name),
            "channel_name": str(channel_name),
            "channel_url": str(channel_url),
            "thumbnail": thumbnail,
            "thumb": thumbnail,
            "views": str(view_count),
            "view_count": str(view_count),
            "published": str(published),
            "video": bool(is_video),
            "message_id": message_id,
            "user": requester,
            "requester": requester,
            "stream_url": raw.get("stream_url")
        }

    async def search(self, query: str, limit: int = 1, requester: str = "Anonymous") -> Optional[Dict[str, Any]]:
        """Fast search returning a single normalized track."""
        results = await self.search_videos(query, limit=limit, requester=requester)
        return results[0] if results else None

    async def search_videos(self, query: str, limit: int = 1, requester: str = "Anonymous") -> List[Dict[str, Any]]:
        """
        Fast async search using yt-search-python VideosSearch with yt_dlp fallback.
        """
        query = query.strip()
        if not query:
            return []

        # 1. Attempt using yt-search-python future VideosSearch
        if HAS_YT_SEARCH:
            try:
                search_inst = VideosSearch(query, limit=limit)
                resp = await search_inst.next()
                results = resp.get("result", [])
                if results:
                    return [self.normalize_track(r, requester=requester) for r in results]
            except Exception as e:
                LOGGER.error(f"yt-search-python search failed for query '{query}': {e}")

        # 2. Fallback to yt_dlp
        return await self._search_many_ytdlp(query, limit=limit, requester=requester)

    async def search_many(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Multi-result search for inline query results."""
        return await self.search_videos(query, limit=limit)

    async def get_video_metadata(self, url_or_id: str) -> Optional[Dict[str, Any]]:
        """Fetches detailed metadata for a single video."""
        canonical_url = resolve_video_url(url_or_id)
        if HAS_YT_SEARCH:
            try:
                vid_obj = Video()
                data = await vid_obj.get(canonical_url)
                if data:
                    return self.normalize_track(data)
            except Exception:
                pass
        return await self.search(canonical_url)

    async def get_recommendations(self, video_id: str, limit: int = 9) -> List[Dict[str, Any]]:
        """
        Fetches related songs using yt-search-python Recommendations or Video.getInfo.
        """
        if not video_id:
            return []

        # 1. Try Recommendations API from yt-search-python
        if HAS_YT_SEARCH:
            try:
                recs_obj = Recommendations(video_id)
                res = await recs_obj.next()
                items = res.get("result", [])
                if items:
                    recs = [self.normalize_track(item) for item in items if item.get("id") != video_id]
                    if recs:
                        return recs[:limit]
            except Exception as e:
                LOGGER.debug(f"Recommendations API failed for {video_id}: {e}")

            # 2. Try Video.get
            try:
                url = resolve_video_url(video_id)
                vid_obj = Video()
                data = await vid_obj.get(url)
                related = data.get("relatedVideos", {}).get("videos", [])
                if related:
                    recs = [self.normalize_track(item) for item in related if item.get("id") != video_id]
                    if recs:
                        return recs[:limit]
            except Exception as e:
                LOGGER.debug(f"Video info related failed for {video_id}: {e}")

        # 3. Fallback search based on track info
        return await self._recommendations_fallback(video_id, limit=limit)

    async def get_playlist(self, url: str, limit: int = 50) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """
        Fetches YouTube Playlists, Mixes (list=RD...), and collections.
        """
        def _extract():
            if yt_dlp is None:
                return None, []
            ydl_opts = {
                "extract_flat": "in_playlist",
                "skip_download": True,
                "quiet": True,
                "no_warnings": True,
                "ignoreerrors": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return None, []
                title = info.get("title") or "YouTube Playlist / Mix"
                raw_entries = info.get("entries") or []
                tracks = []
                for entry in raw_entries:
                    if not entry:
                        continue
                    vid_id = entry.get("id") or entry.get("url")
                    vid_title = entry.get("title")
                    if not vid_id or not vid_title:
                        continue
                    tracks.append(self.normalize_track(entry))
                    if len(tracks) >= limit:
                        break
                return title, tracks

        try:
            return await asyncio.to_thread(_extract)
        except Exception as e:
            LOGGER.error(f"Playlist extraction failed for {url}: {e}")
            return None, []

    async def _search_many_ytdlp(self, query: str, limit: int = 5, requester: str = "Anonymous") -> List[Dict[str, Any]]:
        def _run():
            if yt_dlp is None:
                return []
            ydl_opts = {
                "format": "bestaudio/best",
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "extract_flat": True,
            }
            search_query = query if query.startswith("http") else f"ytsearch{limit}:{query}"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                if not info:
                    return []
                if "entries" in info and info["entries"]:
                    return info["entries"]
                return [info]

        try:
            entries = await asyncio.to_thread(_run)
            return [self.normalize_track(e, requester=requester) for e in entries if e]
        except Exception as e:
            LOGGER.error(f"yt_dlp search_many error: {e}")
            return []

    async def _recommendations_fallback(self, video_id: str, limit: int = 9) -> List[Dict[str, Any]]:
        search_res = await self.search_many(f"related to {video_id}", limit=limit + 1)
        return [t for t in search_res if t.get("id") != video_id][:limit]

YouTube = YouTubeService()
