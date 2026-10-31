import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv():
    env_file = BASE_DIR.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")
DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "")
GUILD_ID = int(os.environ.get("GUILD_ID", "0") or "0")
APPROVAL_CHANNEL_ID = int(os.environ.get("APPROVAL_CHANNEL_ID", "0") or "0")
BACKUP_CHANNEL_ID = int(os.environ.get("BACKUP_CHANNEL_ID", "0") or "0")
ADMIN_ROLE_ID = os.environ.get("ADMIN_ROLE_ID", "")
DOCS_CHANNEL_ID = int(os.environ.get("DOCS_CHANNEL_ID", "0") or "0")
FIVEMANAGE_API_KEY = os.environ.get("FIVEMANAGE_API_KEY", "")
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-production-upd-2026")
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8080").rstrip("/")
API_URL = os.environ.get("API_URL", "http://localhost:8080").rstrip("/")
PORT = int(os.environ.get("PORT", os.environ.get("SERVER_PORT", "8080")))
DB_PATH = os.environ.get("DB_PATH", str(BASE_DIR / "upd_records.db"))
