# Periodic Background Auto Cleanup Routine (Section 13)
import asyncio
import os
import time
import shutil
import psutil
from pathlib import Path
from wirq import config, logger, queue

async def cleanup_worker():
    logger.info(f"Auto-cleanup daemon started (interval: {config.CLEANUP_INTERVAL}s, max age: {config.CLEANUP_MAX_AGE}s).")
    while True:
        try:
            await asyncio.sleep(config.CLEANUP_INTERVAL)
            now = time.time()
            removed_files = 0
            freed_bytes = 0

            # 1. Clean old downloads
            downloads_dir = Path("downloads")
            if downloads_dir.exists():
                for p in downloads_dir.glob("*"):
                    try:
                        if p.is_file():
                            stat = p.stat()
                            if now - stat.st_mtime > config.CLEANUP_MAX_AGE:
                                freed_bytes += stat.st_size
                                p.unlink()
                                removed_files += 1
                    except Exception:
                        pass

            # 2. Clean thumbnail cache
            cache_dir = Path("cache")
            if cache_dir.exists():
                for p in cache_dir.glob("thumb_*.jpg"):
                    try:
                        if p.is_file():
                            stat = p.stat()
                            if now - stat.st_mtime > config.CLEANUP_MAX_AGE:
                                freed_bytes += stat.st_size
                                p.unlink()
                                removed_files += 1
                    except Exception:
                        pass

            # 3. Clean orphaned ffmpeg processes
            for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                try:
                    if proc.info['name'] and 'ffmpeg' in proc.info['name'].lower():
                        # If ffmpeg has been running longer than 4 hours, terminate
                        if now - proc.info['create_time'] > 14400:
                            proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            if removed_files > 0:
                mb_freed = round(freed_bytes / (1024 * 1024), 2)
                logger.info(f"Auto-cleanup cycle: removed {removed_files} files ({mb_freed} MB freed).")

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Error during auto-cleanup: {e}")
