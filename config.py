import os

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = os.environ.get("OWNER_ID")

DATABASE_URL = os.environ.get("DATABASE_URL")

AUTH_CHAT = os.environ.get("AUTH_CHAT", "")  # space-separated IDs
LOGS_CHAT = int(os.environ.get("LOGS_CHAT", 0))
POST_CHAT = int(os.environ.get("POST_CHAT", 0))

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "adminadmin")

SITE_SECRET = os.environ.get("SITE_SECRET", "secret_key")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")

DELETE_AFTER_MINUTES = int(os.environ.get("DELETE_AFTER_MINUTES", 10))
POST_UPDATES = os.environ.get("POST_UPDATES", "True") == "True"
USE_CAPTION = os.environ.get("USE_CAPTION", "False") == "True"

PORT = int(os.environ.get("PORT", 6519))

# Optional multi-token dict from environment (JSON format recommended)
import json
MULTI_TOKENS = json.loads(os.environ.get("MULTI_TOKENS", "{}"))

# Computed values
SUDO_USERS = [int(x) for x in OWNER_ID.split()]
AUTH_CHATS = [int(x) for x in AUTH_CHAT.split() if x]
