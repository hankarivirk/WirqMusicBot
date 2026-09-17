# Changelog - Wirq Music Bot

## [3.2.0] - 2026-09-17
### Added
- Complete Apple Music-inspired player card thumbnail generator using Pillow (blurred ambient backdrop, real album artwork, codec/bitrate pill badges, dynamic progress bar, and requester info).
- 3-State Loop engine (Loop OFF, Loop Current Song, Loop Entire Queue) with persistent database storage.
- Intelligent YouTube recommendation engine and Autoplay mode (toggles automatic queueing vs 3 recommendation buttons + 'More' button).
- Interactive `/search` command with inline buttons for direct playback.
- True fallback localization system for English, Hindi, and Punjabi.
- Multi-tier thumbnail preference resolution: Group Setting > Global Owner Default > ENV value.
- Scheduled background auto-cleanup daemon for stale files, thumbnails, and orphaned FFmpeg processes.
- Comprehensive deployment guides for Termux, Linux VPS, Docker, and GitHub.
