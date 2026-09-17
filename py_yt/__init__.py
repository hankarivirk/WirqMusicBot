import aiohttp
from typing import Dict, Any, List

class VideosSearch:
    def __init__(self, query: str, limit: int = 5, with_live: bool = False, **kwargs):
        self.query = query
        self.limit = limit
        self.with_live = with_live

    async def next(self) -> Dict[str, Any]:
        """Perform Innertube search for high-speed metadata extraction."""
        url = "https://www.youtube.com/youtubei/v1/search"
        payload = {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20240101.00.00",
                    "hl": "en",
                    "gl": "US"
                }
            },
            "query": self.query
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {"result": self._parse_items(data)}
        except Exception:
            pass
        return {"result": []}

    def _parse_items(self, data: dict) -> List[dict]:
        items = []
        try:
            contents = (
                data.get("contents", {})
                .get("twoColumnSearchResultsRenderer", {})
                .get("primaryContents", {})
                .get("sectionListRenderer", {})
                .get("contents", [{}])[0]
                .get("itemSectionRenderer", {})
                .get("contents", [])
            )
            for item in contents:
                vr = item.get("videoRenderer")
                if not vr:
                    continue
                video_id = vr.get("videoId")
                title = vr.get("title", {}).get("runs", [{}])[0].get("text") or "Unknown"
                duration = vr.get("lengthText", {}).get("simpleText") or "00:00"
                channel = vr.get("ownerText", {}).get("runs", [{}])[0].get("text") or ""
                thumbs = vr.get("thumbnail", {}).get("thumbnails", [{}])
                views = vr.get("viewCountText", {}).get("simpleText") or ""
                items.append({
                    "id": video_id,
                    "title": title,
                    "duration": duration,
                    "channel": {"name": channel},
                    "thumbnails": thumbs,
                    "link": f"https://www.youtube.com/watch?v={video_id}",
                    "viewCount": {"short": views},
                })
                if len(items) >= self.limit:
                    break
        except Exception:
            pass
        return items

class Recommendations:
    @staticmethod
    async def get(video_id: str, limit: int = 12) -> List[dict]:
        """Extract real YouTube related recommendations using Innertube watch next endpoint."""
        url = "https://www.youtube.com/youtubei/v1/next"
        payload = {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20240101.00.00",
                    "hl": "en",
                    "gl": "US"
                }
            },
            "videoId": video_id
        }
        items = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = (
                            data.get("contents", {})
                            .get("twoColumnWatchNextResults", {})
                            .get("secondaryResults", {})
                            .get("secondaryResults", {})
                            .get("results", [])
                        )
                        for item in results:
                            cvr = item.get("compactVideoRenderer")
                            if not cvr:
                                continue
                            vid = cvr.get("videoId")
                            if not vid:
                                continue
                            title = cvr.get("title", {}).get("simpleText") or cvr.get("title", {}).get("runs", [{}])[0].get("text") or "YouTube Track"
                            duration = cvr.get("lengthText", {}).get("simpleText") or "00:00"
                            channel = cvr.get("shortBylineText", {}).get("runs", [{}])[0].get("text") or "YouTube"
                            thumbs = cvr.get("thumbnail", {}).get("thumbnails", [{}])
                            items.append({
                                "id": vid,
                                "title": title,
                                "duration": duration,
                                "channel": {"name": channel},
                                "thumbnails": thumbs,
                                "link": f"https://www.youtube.com/watch?v={vid}",
                            })
                            if len(items) >= limit:
                                break
        except Exception:
            pass
        return items

class Playlist:
    def __init__(self, url: str, limit: int = 50):
        self.url = url
        self.limit = limit
