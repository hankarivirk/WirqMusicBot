import shutil
from pathlib import Path

from anony import logger


def ensure_dirs():
    for directory in ("cache", "downloads", ".cache/yt-dlp"):
        Path(directory).mkdir(parents=True, exist_ok=True)

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required and was not found in PATH.")
    logger.info("FFmpeg binary detected at: %s", ffmpeg)
