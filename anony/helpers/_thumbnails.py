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
        self.art = (440, 440)
        self.white = (255, 255, 255, 255)
        self.dim = (230, 230, 235, 255)
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
        brand = f"{config.BRAND_NAME}|{config.BRAND_TAG}"
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

    def _glass_panel(self, base: Image.Image, box, radius, opacity=70, blur=22, tint=(255, 255, 255)):
        """Frost the region of `base` under `box` and composite it back in, liquid-glass style."""
        x1, y1, x2, y2 = box
        w, h = x2 - x1, y2 - y1
        region = base.crop(box).filter(ImageFilter.GaussianBlur(blur))
        region = ImageEnhance.Brightness(region).enhance(1.12)
        tint_layer = Image.new("RGBA", (w, h), tint + (opacity,))
        glass = Image.alpha_composite(region.convert("RGBA"), tint_layer)
        mask = _round_mask((w, h), radius)
        base.paste(glass, (x1, y1), mask)
        draw = ImageDraw.Draw(base)
        draw.rounded_rectangle(box, radius=radius, outline=(255, 255, 255, 90), width=2)

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

                # Blurred, dimmed backdrop
                bg = ImageOps.fit(raw, size, method=Image.LANCZOS, centering=(0.5, 0.4))
                bg = bg.filter(ImageFilter.GaussianBlur(35))
                bg = ImageEnhance.Brightness(bg).enhance(0.38)
                bg = ImageEnhance.Color(bg).enhance(1.25)
                image = bg.convert("RGBA")

                # Album art card, floating with a soft shadow
                art_pos = ((size[0] - self.art[0]) // 2, 46)
                shadow = Image.new("RGBA", size, (0, 0, 0, 0))
                ImageDraw.Draw(shadow).rounded_rectangle(
                    (art_pos[0] - 6, art_pos[1] + 14, art_pos[0] + self.art[0] + 6, art_pos[1] + self.art[1] + 26),
                    radius=34, fill=(0, 0, 0, 130),
                )
                shadow = shadow.filter(ImageFilter.GaussianBlur(24))
                image = Image.alpha_composite(image, shadow)

                art = ImageOps.fit(raw, self.art, method=Image.LANCZOS, centering=(0.5, 0.5))
                art_mask = _round_mask(self.art, 30)
                art.putalpha(art_mask)
                image.paste(art, art_pos, art)
                draw = ImageDraw.Draw(image)
                draw.rounded_rectangle(
                    (art_pos[0], art_pos[1], art_pos[0] + self.art[0], art_pos[1] + self.art[1]),
                    radius=30, outline=(255, 255, 255, 110), width=3,
                )

                # Brand pill, top-left — liquid glass badge
                image = image.convert("RGBA")
                brand = config.BRAND_NAME or getattr(app, "name", None) or "Music"
                self._glass_panel(image, (36, 30, 236, 78), radius=24, opacity=55, blur=18)
                draw = ImageDraw.Draw(image)
                draw.text((56, 40), f"♫ {brand}", font=self.font_bold(20), fill=self.white)

                # Quality pill, top-right
                tag = config.BRAND_TAG.upper()
                tag_w = draw.textlength(tag, font=self.font_bold(18)) + 44
                self._glass_panel(image, (size[0] - 36 - int(tag_w), 30, size[0] - 36, 74), radius=22, opacity=55, blur=18)
                draw = ImageDraw.Draw(image)
                draw.text((size[0] - 36 - int(tag_w) + 22, 40), tag, font=self.font_bold(18), fill=self.white)

                # Bottom liquid-glass info panel
                panel_box = (40, 520, size[0] - 40, size[1] - 32)
                self._glass_panel(image, panel_box, radius=32, opacity=60, blur=26)
                draw = ImageDraw.Draw(image)

                title = song.title[:46] + ("…" if len(song.title) > 46 else "")
                draw.text((72, 548), title, font=self.font_bold(34), fill=self.white)

                requester = song.user or "Autoplay"
                subtitle = f"{(song.channel_name or 'Unknown')[:28]}  •  Requested by {requester}"
                draw.text((72, 596), subtitle, font=self.font_light(20), fill=self.dim)

                # Progress bar
                bar_y = 648
                bar_left, bar_right = 72, size[0] - 72
                draw.line([(bar_left, bar_y), (bar_right, bar_y)], fill=(255, 255, 255, 70), width=4)
                draw.ellipse((bar_left - 6, bar_y - 6, bar_left + 6, bar_y + 6), fill=self.white)
                draw.text((bar_left, bar_y + 14), "0:00", font=self.font_bold(18), fill=self.dim)
                dur_w = draw.textlength(song.duration, font=self.font_bold(18))
                draw.text((bar_right - dur_w, bar_y + 14), song.duration, font=self.font_bold(18), fill=self.white)

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
