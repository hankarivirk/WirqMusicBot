import os
from dotenv import load_dotenv

load_dotenv()

# Mandatory Telegram API & Core Credentials
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
LOGGER_ID = int(os.getenv("LOGGER_ID") or os.getenv("LOG_GROUP_ID") or "0")
MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGO_DB_URI") or ""

# Assistant String Sessions (Session & Session1 unified)
SESSION = os.getenv("SESSION") or os.getenv("STRING_SESSION") or os.getenv("SESSION1") or ""
SESSION1 = SESSION
SESSION2 = os.getenv("SESSION2") or os.getenv("STRING_SESSION2") or ""
SESSION3 = os.getenv("SESSION3") or os.getenv("STRING_SESSION3") or ""
SESSION4 = os.getenv("SESSION4") or os.getenv("STRING_SESSION4") or ""
SESSION5 = os.getenv("SESSION5") or os.getenv("STRING_SESSION5") or ""

# Bot Identity
BOT_NAME = "MUSIC FLOW"
BOT_USERNAME = os.getenv("BOT_USERNAME", "")

# Optional Contact & Asset URLs (Zero hardcoded external links)
OWNER_URL = os.getenv("OWNER_URL", "").strip()
START_IMG_URL = os.getenv("START_IMG_URL", "").strip()
DEFAULT_THUMB_URL = os.getenv("DEFAULT_THUMB_URL", "").strip()
PING_IMG_URL = os.getenv("PING_IMG_URL", "").strip()

# Sudo Management
SUDO_USERS = list(map(int, os.getenv("SUDO_USERS", "").split())) if os.getenv("SUDO_USERS") else []
if OWNER_ID and OWNER_ID not in SUDO_USERS:
    SUDO_USERS.append(OWNER_ID)

# Operational Limits
DURATION_LIMIT_MIN = int(os.getenv("DURATION_LIMIT", "300"))
PLAYLIST_FETCH_LIMIT = int(os.getenv("PLAYLIST_FETCH_LIMIT", "50"))

# Compatibility Aliases
MONGO_DB_URI = MONGO_URL
LOG_GROUP_ID = LOGGER_ID
STRING_SESSION = SESSION
STRING_SESSION2 = SESSION2
STRING_SESSION3 = SESSION3
STRING_SESSION4 = SESSION4
STRING_SESSION5 = SESSION5
