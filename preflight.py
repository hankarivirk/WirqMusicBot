"""Fast deployment preflight for Railway/VPS."""
import importlib
import shutil
import sys
import pathlib

# These names are the import names, not necessarily the PyPI names.
REQUIRED = (
    "pyrogram",
    "pytgcalls",
    "pymongo",
    "yt_dlp",
    "aiohttp",
    "PIL",
    "httpx",
    "dotenv",
    "psutil",
    "tgcrypto",
)

missing = []
for name in REQUIRED:
    try:
        importlib.import_module(name)
    except Exception as exc:
        missing.append(f"{name}: {type(exc).__name__}: {exc}")

if missing:
    print("PRE-FLIGHT FAILED: missing/broken Python dependencies:")
    for item in missing:
        print(" -", item)
    raise SystemExit(1)

# The project vendors these two packages in the repository, so verify the
# actual source tree is importable instead of relying on a separately
# installed youtubesearchpython package.
try:
    import httpx  # noqa: F401
    import youtubesearchpython  # noqa: F401
    import py_yt  # noqa: F401
except Exception as exc:
    print(f"PRE-FLIGHT FAILED: YouTube search stack: {type(exc).__name__}: {exc}")
    raise SystemExit(1)

import pyrogram
import pytgcalls
from pymongo import AsyncMongoClient
from pyrogram.raw import types

# AsyncMongoClient is used directly by anony/core/mongo.py.  It became part
# of PyMongo's async API before 4.13 and is now the supported async driver.
if not AsyncMongoClient:
    raise SystemExit("PRE-FLIGHT FAILED: PyMongo AsyncMongoClient is unavailable.")

# PyTgCalls 2.x needs the modern Telegram raw voice-call layer supplied by
# the pinned PyroTGFork release.
needed_raw = (
    "InputGroupCall",
    "InputGroupCallInviteMessage",
    "InputGroupCallSlug",
    "InputGroupCallStream",
)
missing_raw = [name for name in needed_raw if not hasattr(types, name)]
if missing_raw:
    print("PRE-FLIGHT FAILED: Telegram raw layer is too old/incompatible.")
    print("Missing:", ", ".join(missing_raw))
    print("Install pyrotgfork==2.2.24 with py-tgcalls==2.3.3.")
    raise SystemExit(1)

from pytgcalls import types as call_types
from pytgcalls.exceptions import NoActiveGroupCall

for name in ("MediaStream", "StreamEnded", "ChatUpdate"):
    if not hasattr(call_types, name):
        raise SystemExit(f"PRE-FLIGHT FAILED: PyTgCalls is missing types.{name}.")
if NoActiveGroupCall is None:
    raise SystemExit("PRE-FLIGHT FAILED: PyTgCalls exception API is incompatible.")

# Validate the local source tree before startup so deployment fails with a
# useful message instead of a nested import traceback.
for required_path in ("anony", "py_yt", "youtubesearchpython", "config.py"):
    if not pathlib.Path(required_path).exists():
        raise SystemExit(f"PRE-FLIGHT FAILED: required project path is missing: {required_path}")


# Verify the MongoDB async client is not constructed at import time.
# This is intentionally a source-level guard because an AsyncMongoClient
# created before asyncio.run(main()) can bind futures to a different loop.
mongo_source = pathlib.Path("anony/core/mongo.py")
if mongo_source.exists():
    mongo_text = mongo_source.read_text(encoding="utf-8")
    if "self.mongo = AsyncMongoClient(config.MONGO_URL" in mongo_text.split("async def connect", 1)[0]:
        raise SystemExit(
            "PRE-FLIGHT FAILED: AsyncMongoClient is created before the application event loop."
        )

for binary in ("ffmpeg", "ffprobe", "aria2c", "deno"):
    if shutil.which(binary) is None:
        raise SystemExit(f"PRE-FLIGHT FAILED: {binary} is not installed or not on PATH.")

# Full YouTube extraction now depends on the EJS solver package plus a supported
# JavaScript runtime. Check both at startup so a broken image fails clearly
# instead of surfacing later as the vague "couldn't fetch file" error.
try:
    import yt_dlp_ejs  # noqa: F401
except Exception as exc:
    raise SystemExit(
        f"PRE-FLIGHT FAILED: yt-dlp-ejs is unavailable: {type(exc).__name__}: {exc}"
    )

print(
    f"PRE-FLIGHT OK | Python {sys.version.split()[0]} | "
    f"Pyrogram {getattr(pyrogram, '__version__', '?')} | "
    f"PyTgCalls {getattr(pytgcalls, '__version__', '?')} | FFmpeg OK"
)
