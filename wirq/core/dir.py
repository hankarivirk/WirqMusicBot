import shutil
from pathlib import Path
from wirq import logger

def ensure_dirs():
    if not shutil.which("ffmpeg"):
        logger.warning("FFmpeg was not found in system PATH. Voice chat audio streaming requires FFmpeg.")
    for d in ["cache", "downloads", "wirq/cookies"]:
        Path(d).mkdir(parents=True, exist_ok=True)
    logger.info("Directories initialized.")
