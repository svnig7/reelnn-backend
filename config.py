# Main configuration file

# Mandatory Variables
API_ID = 1111111 # Replace with your actual Telegram API ID
API_HASH = "your_api_hash_here"  # Replace with your actual Telegram API Hash
BOT_TOKEN = "your_bot_token_here"  # Replace with your actual Bot Token
OWNER_ID = "11111111"  # Replace with your actual Owner ID
# Database
DATABASE_URL = "your_database_url_here"  # Replace with your actual database URL

AUTH_CHAT = "-100123456789 -1001234567890" # Replace with your actual auth chat ID. You can use multiple IDs separated by ( space ).
LOGS_CHAT = -1001234567891 # Replace with your actual logs chat ID
POST_CHAT = -1001234567891 # Replace with your actual post chat ID

ADMIN_USERNAME = "admin" # Replace with your admin username
ADMIN_PASSWORD = "adminadmin" # Replace with your admin password

SITE_SECRET = "your_secret_key" # Replace with your site secret key
TMDB_API_KEY = "" # Replace with your TMDB API key

SITE_NAME = "reelnn"
POST_CHAT_LINK = "https://t.me/reelnnUpdates"
ENABLE_REGISTRATION = False
SIGNUP_IMAGE = "https://i.ibb.co/dJ2t5bsF/anime-AI-1.jpg"
SIGNUP_MESSAGE = """
**Heyaa** 🙋🏻‍♀️\n
**Welcome to reelnn!** 🎬 
Your ultimate destination for entertainment!
To get started and access our media library,
please register your account.

👉 Use the /register command to sign up for the site.
"""


# Optional Variables

# If you want to use multiple bot tokens, uncomment the MULTI_TOKENS dictionary and add your tokens. this aditional bots will speed up the process of downloading and streaming files.
MULTI_TOKENS = {
    # 1: "BOT_TOKEN_1_HERE",
    # 2: "BOT_TOKEN_2_HERE",
    # Add more tokens as needed
}
DELETE_AFTER_MINUTES = 10 # Set the number of minutes after which files will be deleted from user message
POST_UPDATES = True # Set to True if you want to post updates in the post chat
USE_CAPTION = False # Set to True if you want to use captions for posts instead of file names.

# Port configuration
import os
PORT = int(os.environ.get("PORT", 6519))
















# (Don't touch this unless you know what you're doing)
SUDO_USERS = [int(x) for x in (OWNER_ID).split()]
AUTH_CHATS = [int(x) for x in (AUTH_CHAT).split()]