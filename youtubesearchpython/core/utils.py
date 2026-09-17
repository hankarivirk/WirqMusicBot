def normalize_thumbnails(thumbnails, video_id):
    return thumbnails or [{"url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"}]
