# Compatibility shim so `from py_yt import Playlist, VideosSearch`
# (the py-yt-search API Wirq Music Bot is written against) keeps working
# against the vendored yt-search-python "legacy" fork, which ships
# the same async classes under youtubesearchpython.future.
#
# This package is not a real py-yt-search install — it's a thin
# re-export layer over ./youtubesearchpython (vendored at the repo
# root, alongside this package, so it must stay importable as a
# top-level module).

from typing import Optional

from youtubesearchpython.future import (
    Playlist,
    VideosSearch as _VideosSearch,
    Search,
    ChannelsSearch,
    PlaylistsSearch,
    ChannelSearch,
    CustomSearch,
    Video,
    Suggestions,
    SuggestionsSession,
    Hashtag,
    Comments,
    Transcript,
    Channel,
    Recommendations,
)
from youtubesearchpython.core.constants import ResultMode


class VideosSearch(_VideosSearch):
    """py-yt-search compatible VideosSearch.

    Wirq Music Bot calls this with a `with_live` kwarg, which the vendored
    legacy library doesn't have — it uses `is_live` instead, and only
    supports "videos only" or "livestreams only" (no mixed mode).

    `with_live=False` (Wirq Music Bot's only real usage) maps cleanly onto
    the library's default "videos only" mode. `with_live=True` is
    accepted for API compatibility but still returns videos only,
    since this fork can't mix both result types in one search.
    """

    def __init__(
        self,
        query: str,
        limit: int = 20,
        language: str = "en",
        region: str = "US",
        timeout: Optional[int] = None,
        with_live: Optional[bool] = None,
        **kwargs,
    ):
        super().__init__(
            query,
            limit=limit,
            language=language,
            region=region,
            timeout=timeout,
            is_live=None,
            **kwargs,
        )

__all__ = [
    "Playlist",
    "VideosSearch",
    "Search",
    "ChannelsSearch",
    "PlaylistsSearch",
    "ChannelSearch",
    "CustomSearch",
    "Video",
    "Suggestions",
    "SuggestionsSession",
    "Hashtag",
    "Comments",
    "Transcript",
    "Channel",
    "Recommendations",
    "ResultMode",
]

__title__ = "py_yt (compat shim over vendored yt-search-python)"
