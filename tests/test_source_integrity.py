from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_globals_are_not_captured_by_core_modules():
    forbidden = {"app", "userbot", "db", "lang", "tg", "yt", "queue", "thumb", "anon"}
    for path in (ROOT / "anony" / "core").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module == "anony":
                names = {a.name for a in node.names}
                assert not (names & forbidden), f"{path}: captures runtime global(s): {names & forbidden}"


def test_required_playback_methods_exist_in_source():
    queue = (ROOT / "anony/helpers/_queue.py").read_text(encoding="utf-8")
    calls = (ROOT / "anony/core/calls.py").read_text(encoding="utf-8")
    youtube = (ROOT / "anony/core/youtube.py").read_text(encoding="utf-8")
    assert "def set_current(" in queue
    assert "anony.queue.set_current(" in calls
    assert "async def get_stream_url(" in youtube
    assert "async def download(" in youtube


def test_playback_fallbacks_are_wired_correctly():
    play = (ROOT / "anony/plugins/play.py").read_text(encoding="utf-8")
    calls = (ROOT / "anony/core/calls.py").read_text(encoding="utf-8")
    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "from anony import anon, app, config, db, lang, logger, queue, tg, yt" in play
    assert "direct_stream_used = False" in play
    assert "if not started and direct_stream_used" in play
    assert "headers = None" in calls
    assert "if direct_stream_used and isinstance(media, Track):" in calls
    assert "    unzip " in docker
    assert "python -m yt_dlp --version" in docker


def test_no_runtime_credentials_or_sessions():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.name.startswith(".env") or path.suffix in {".session", ".session-journal"}:
            raise AssertionError(f"runtime credential/state file present: {path}")
