import hashlib
import os
import asyncio
import aiohttp
from PIL import (Image, ImageDraw, ImageEnhance,
                 ImageFilter, ImageFont, ImageOps)

from anony import app, config, logger
from anony.helpers import Track


def _round_mask(size, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return mask


class Thumbnail:
    def __init__(self):
        self.canvas = (1280, 720)
        self.art = 380
        self.white = (255, 255, 255, 255)
        self.dim = (225, 225, 232, 210)
        self.faint = (255, 255, 255, 150)
        self.font_bold = lambda s: ImageFont.truetype("anony/helpers/Raleway-Bold.ttf", s)
        self.font_light = lambda s: ImageFont.truetype("anony/helpers/Inter-Light.ttf", s)
        self.session: aiohttp.ClientSession | None = None
        # Per-song locks so two concurrent requests for the same track's
        # thumbnail can't race on the same temp/output file paths.
        self.locks: dict[str, asyncio.Lock] = {}

    def _brand_tag(self) -> str:
        """Short hash of the branding-relevant config, mixed into the
        cache filename so a branding change (name/tag) invalidates stale
        cached thumbnails instead of silently reusing them."""
        brand = f"{config.BRAND_NAME}|{config.BRAND_TAG}|v2"
        return hashlib.sha1(brand.encode()).hexdigest()[:8]

    async def start(self) -> None:
        self.session = aiohttp.ClientSession()

    async def close(self) -> None:
        await self.session.close()

    async def save_thumb(self, output_path: str, url: str) -> str:
        async with self.session.get(url) as resp:
            with open(output_path, "wb") as f:
                f.write(await resp.read())
        return output_path

    @staticmethod
    def _vignette(size: tuple[int, int]) -> Image.Image:
        """A soft radial darkening toward the edges — the trick Apple
        Music's now-playing screen uses so text/art read clearly over a
        busy blurred photo without needing an opaque panel behind them."""
        mask = Image.new("L", size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse(
            (-size[0] * 0.3, -size[1] * 0.4, size[0] * 1.3, size[1] * 1.25),
            fill=150,
        )
        return mask.filter(ImageFilter.GaussianBlur(160))

    async def generate(self, song: Track, size=None) -> str:
        size = size or self.canvas
        lock = self.locks.setdefault(song.id, asyncio.Lock())
        async with lock:
            try:
                temp = f"cache/temp_{song.id}_{os.getpid()}_{id(lock)}.jpg"
                output = f"cache/{song.id}_{self._brand_tag()}.png"
                if os.path.exists(output):
                    return output

                await self.save_thumb(temp, song.thumbnail)
                raw = Image.open(temp).convert("RGBA")

                # --- Backdrop: the artwork itself, blown up, heavily
                # blurred, saturated and darkened — Apple Music's
                # now-playing background is literally this, no separate
                # brand color needed, so it always matches the song. ---
                bg = ImageOps.fit(raw, size, method=Image.LANCZOS, centering=(0.5, 0.5))
                bg = bg.filter(ImageFilter.GaussianBlur(70))
                bg = ImageEnhance.Color(bg).enhance(1.45)
                bg = ImageEnhance.Contrast(bg).enhance(1.1)
                bg = ImageEnhance.Brightness(bg).enhance(0.55)
                image = bg.convert("RGBA")

                dark = Image.new("RGBA", size, (8, 8, 12, 255))
                image = Image.composite(image, dark, self._vignette(size))

                # --- Album art: centered, true square, soft continuous
                # corners, a soft floating shadow — no outline stroke,
                # no border; Apple never outlines the artwork. ---
                art_pos = ((size[0] - self.art) // 2, 86)
                shadow = Image.new("RGBA", size, (0, 0, 0, 0))
                ImageDraw.Draw(shadow).rounded_rectangle(
                    (art_pos[0] - 2, art_pos[1] + 26,
                     art_pos[0] + self.art + 2, art_pos[1] + self.art + 40),
                    radius=42, fill=(0, 0, 0, 170),
                )
                shadow = shadow.filter(ImageFilter.GaussianBlur(34))
                image = Image.alpha_composite(image, shadow)

                art = ImageOps.fit(raw, (self.art, self.art), method=Image.LANCZOS, centering=(0.5, 0.5))
                art.putalpha(_round_mask((self.art, self.art), 36))
                image.paste(art, art_pos, art)

                draw = ImageDraw.Draw(image)

                # --- Title + artist, centered underneath the art,
                # Apple's now-playing hierarchy: bold title, lighter
                # smaller artist line right below it. ---
                text_top = art_pos[1] + self.art + 46
                title = song.title[:42] + ("…" if len(song.title) > 42 else "")
                title_font = self.font_bold(40)
                title_w = draw.textlength(title, font=title_font)
                draw.text(((size[0] - title_w) / 2, text_top), title, font=title_font, fill=self.white)

                artist = (song.channel_name or "Unknown Artist")[:42]
                artist_font = self.font_light(24)
                artist_w = draw.textlength(artist, font=artist_font)
                draw.text(((size[0] - artist_w) / 2, text_top + 54), artist, font=artist_font, fill=self.dim)

                # --- Slim capsule progress bar with a small scrubber
                # dot, times at either end — the exact Apple Music
                # now-playing scrubber, minus the glass panel behind it. ---
                bar_y = text_top + 118
                bar_left, bar_right = size[0] // 2 - 260, size[0] // 2 + 260
                draw.line([(bar_left, bar_y), (bar_right, bar_y)], fill=(255, 255, 255, 60), width=5)
                draw.ellipse((bar_left - 7, bar_y - 7, bar_left + 7, bar_y + 7), fill=self.white)

                time_font = self.font_bold(16)
                draw.text((bar_left, bar_y + 16), "0:00", font=time_font, fill=self.faint)
                dur_w = draw.textlength(song.duration, font=time_font)
                draw.text((bar_right - dur_w, bar_y + 16), song.duration, font=time_font, fill=self.faint)

                # --- Quiet branding + requester credit, small plain
                # text tucked in the corners instead of loud pill badges. ---
                brand = config.BRAND_NAME or getattr(app, "name", None) or "Music"
                draw.text((44, 42), f"♪ {brand}", font=self.font_bold(19), fill=self.faint)

                requester = song.user or "Autoplay"
                req_text = f"Requested by {requester}"
                req_font = self.font_light(18)
                req_w = draw.textlength(req_text, font=req_font)
                draw.text((size[0] - 44 - req_w, 45), req_text, font=req_font, fill=self.faint)

                image.convert("RGB").save(output)
                try:
                    os.remove(temp)
                except Exception:
                    pass
                return output
            except Exception as e:
                # Log the real failure instead of silently treating every
                # error (network, PIL, disk) identically to "no thumbnail".
                logger.warning(f"Thumbnail generation failed for {song.id}: {e}")
                return config.DEFAULT_THUMB
            finally:
                self.locks.pop(song.id, None)
