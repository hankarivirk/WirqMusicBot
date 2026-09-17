import os
import aiohttp
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config import Config
from wirq import logger
from wirq.helpers._dataclass import Track

config = Config()

class Thumbnail:
    def __init__(self):
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.font_bold_path = Path("wirq/helpers/assets/fonts/DejaVuSans-Bold.ttf")
        self.font_reg_path = Path("wirq/helpers/assets/fonts/DejaVuSans.ttf")
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _download_cover(self, url: str, dest_path: Path) -> bool:
        if dest_path.exists():
            return True
        try:
            session = await self._get_session()
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    with open(dest_path, "wb") as f:
                        f.write(data)
                    return True
        except Exception as e:
            logger.warning(f"Failed to download artwork from {url}: {e}")
        return False

    async def generate(
        self,
        track: Track,
        elapsed_sec: int = 0,
        is_video: bool = False,
        codec: str = "OPUS",
        bitrate: str = "160 KBPS",
        video_quality: str = "720p HD",
        loop_status: str = "OFF",
        autoplay_status: str = "ON",
    ) -> str:
        """Generate an Apple Music-inspired player card with dynamic progress,
        mode badge, real stream codec/bitrate, and branding."""
        if not track:
            return config.DEFAULT_THUMB

        card_path = self.cache_dir / f"card_{track.id}_{elapsed_sec}.jpg"
        if card_path.exists():
            return str(card_path)

        # 1. Download or load cover
        cover_path = self.cache_dir / f"art_{track.id}.jpg"
        has_cover = False
        if track.thumbnail:
            has_cover = await self._download_cover(track.thumbnail, cover_path)

        W, H = 1280, 720
        # Base background
        if has_cover and cover_path.exists():
            try:
                base_img = Image.open(cover_path).convert("RGB")
                bg = base_img.resize((W, H)).filter(ImageFilter.GaussianBlur(35))
                overlay = Image.new("RGBA", (W, H), (12, 12, 18, 190))
                bg.paste(overlay, (0, 0), overlay)
                card = bg.convert("RGB")
            except Exception:
                card = Image.new("RGB", (W, H), color=(18, 18, 24))
        else:
            card = Image.new("RGB", (W, H), color=(18, 18, 24))

        draw = ImageDraw.Draw(card)

        # Load fonts with fallback
        try:
            f_title = ImageFont.truetype(str(self.font_bold_path), 36)
            f_artist = ImageFont.truetype(str(self.font_reg_path), 24)
            f_meta = ImageFont.truetype(str(self.font_bold_path), 16)
            f_small = ImageFont.truetype(str(self.font_reg_path), 18)
            f_footer = ImageFont.truetype(str(self.font_reg_path), 16)
        except Exception:
            f_title = f_artist = f_meta = f_small = f_footer = ImageFont.load_default()

        # 2. Left side Album Art (460x460) with rounded corners
        art_size = 460
        art_x, art_y = 80, 130
        if has_cover and cover_path.exists():
            try:
                cover_img = Image.open(cover_path).convert("RGB").resize((art_size, art_size))
                mask = Image.new("L", (art_size, art_size), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle([0, 0, art_size, art_size], radius=24, fill=255)
                card.paste(cover_img, (art_x, art_y), mask)
            except Exception:
                draw.rounded_rectangle([art_x, art_y, art_x + art_size, art_y + art_size], radius=24, fill=(40, 40, 50))
        else:
            draw.rounded_rectangle([art_x, art_y, art_x + art_size, art_y + art_size], radius=24, fill=(40, 40, 50))
            draw.text((art_x + 130, art_y + 210), "WIRQ MUSIC", font=f_title, fill=(200, 200, 210))

        # Thin outer stroke for album art
        draw.rounded_rectangle([art_x - 2, art_y - 2, art_x + art_size + 2, art_y + art_size + 2], radius=26, outline=(255, 255, 255, 45), width=2)

        # 3. Right side layout
        rx = 590

        # Mode Badge (Audio vs Video)
        if is_video:
            draw.rounded_rectangle([rx, 130, rx + 160, 166], radius=8, fill=(180, 40, 120))
            draw.text((rx + 16, 138), f"VIDEO • {video_quality}", font=f_meta, fill=(255, 255, 255))
        else:
            draw.rounded_rectangle([rx, 130, rx + 140, 166], radius=8, fill=(30, 144, 255))
            draw.text((rx + 16, 138), "AUDIO STREAM", font=f_meta, fill=(255, 255, 255))

        # Codec & Bitrate Badge
        draw.rounded_rectangle([rx + 175, 130, rx + 440, 166], radius=8, fill=(45, 45, 58))
        draw.text((rx + 190, 138), f"{codec} • {bitrate} • LOSSLESS", font=f_meta, fill=(215, 215, 230))

        # Song Title (truncated cleanly)
        raw_title = track.title or "Unknown Track"
        display_title = raw_title if len(raw_title) <= 28 else raw_title[:26] + "..."
        draw.text((rx, 195), display_title, font=f_title, fill=(255, 255, 255))

        # Artist / Channel Name
        artist_name = track.channel_name or "YouTube Music"
        draw.text((rx, 248), artist_name, font=f_artist, fill=(175, 180, 195))

        # Status Indicators (Loop & Autoplay)
        status_text = f"🔁 Loop: {loop_status}    |    ⚡ Autoplay: {autoplay_status}"
        draw.text((rx, 310), status_text, font=f_small, fill=(200, 205, 215))

        # Requester
        req_user = getattr(track, "user", None) or "@wirq4"
        draw.text((rx, 350), f"👤 Requested by: {req_user}", font=f_small, fill=(170, 175, 185))

        # Progress bar
        total_sec = max(track.duration_sec, 1)
        cur_sec = min(max(elapsed_sec, 0), total_sec)
        pct = cur_sec / total_sec

        bar_w = 590
        bar_y = 445

        # Format timestamps
        cur_time_str = f"{cur_sec // 60:02d}:{cur_sec % 60:02d}"
        tot_time_str = track.duration or f"{total_sec // 60:02d}:{total_sec % 60:02d}"

        draw.text((rx, bar_y - 28), cur_time_str, font=f_small, fill=(190, 195, 205))
        draw.text((rx + bar_w - 55, bar_y - 28), tot_time_str, font=f_small, fill=(190, 195, 205))

        # Track background
        draw.rounded_rectangle([rx, bar_y, rx + bar_w, bar_y + 8], radius=4, fill=(55, 55, 68))
        # Track filled progress
        fill_w = max(int(bar_w * pct), 8)
        draw.rounded_rectangle([rx, bar_y, rx + fill_w, bar_y + 8], radius=4, fill=(255, 255, 255))
        # Thumb indicator
        thumb_x = rx + fill_w
        draw.ellipse([thumb_x - 7, bar_y - 4, thumb_x + 9, bar_y + 12], fill=(255, 255, 255))

        # Bottom divider & footer branding
        draw.line([(80, 645), (1200, 645)], fill=(50, 50, 62), width=1)
        draw.text((80, 660), f"{config.BRAND_NAME}  •  {config.BRAND_TAG}", font=f_footer, fill=(140, 145, 155))
        draw.text((950, 660), "Hankarivirk/WirqMusicbot", font=f_footer, fill=(140, 145, 155))

        card.save(card_path, format="JPEG", quality=92)
        return str(card_path)
