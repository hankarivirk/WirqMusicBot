from enum import Enum

searchKey = ""
userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

class ResultMode(int, Enum):
    json = 0
    dict = 1

class SearchMode(str, Enum):
    videos = "EgIQAQ%3D%3D"
    channels = "EgIQAg%3D%3D"
    playlists = "EgIQAw%3D%3D"
    livestreams = "EgJAAQ%3D%3D"
