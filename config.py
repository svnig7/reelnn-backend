# Main configuration file

import os

# Mandatory Variables from Environment
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = os.environ.get("OWNER_ID")
DATABASE_URL = os.environ.get("DATABASE_URL")

AUTH_CHAT = os.environ.get("AUTH_CHAT")  # Space-separated chat IDs
LOGS_CHAT = int(os.environ.get("LOGS_CHAT"))
POST_CHAT = int(os.environ.get("POST_CHAT"))

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

SITE_SECRET = os.environ.get("SITE_SECRET")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")

SITE_NAME = os.environ.get("SITE_NAME", "7 CINEMA")
POST_CHAT_LINK = os.environ.get("POST_CHAT_LINK", "https://t.me/bots_7_bots")
ENABLE_REGISTRATION = os.environ.get("ENABLE_REGISTRATION", "True")
SIGNUP_IMAGE = os.environ.get("SIGNUP_IMAGE", "https://raw.githubusercontent.com/svnig7/svnig7/refs/heads/main/cinemabotl.png")
SIGNUP_MESSAGE = os.environ.get("SIGNUP_MESSAGE", """
**Hey** 🙋🏻‍♀️\n
**Welcome to 7 Cinema !** 🎬

Your ultimate destination for entertainment !
To get started and access our media library,
please register your account.

👉 Use the /register command to sign up for the site.
""")

# Optional Variables
# Uncomment and define these in your environment if needed
MULTI_TOKENS = {
    # 1: os.environ.get("BOT_TOKEN_1"),
    # 2: os.environ.get("BOT_TOKEN_2"),
    # Add more as needed
}

DELETE_AFTER_MINUTES = int(os.environ.get("DELETE_AFTER_MINUTES", 10))
POST_UPDATES = os.environ.get("POST_UPDATES", "False")
USE_CAPTION = os.environ.get("USE_CAPTION", "False")

# Port configuration
PORT = int(os.environ.get("PORT", 8080))

# Internal Configuration (Do not change unless you know what you're doing)
SUDO_USERS = [int(x) for x in OWNER_ID.split()]
AUTH_CHATS = [int(x) for x in AUTH_CHAT.split()]
