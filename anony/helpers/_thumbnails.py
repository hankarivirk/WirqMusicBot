from typing import Optional
import config

def get_thumbnail_url(track_thumb: Optional[str] = None) -> Optional[str]:
    """
    Returns URL-based thumbnail.
    Never relies on local image assets.
    Returns None if no thumbnail or fallback is configured.
    """
    if track_thumb and track_thumb.startswith("http"):
        return track_thumb
    return config.DEFAULT_THUMB_URL if config.DEFAULT_THUMB_URL else None
