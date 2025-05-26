
# reelnn-backend

A asynchronous backend framework for reelnn. Built with FastAPI, Pyrogram, MongoDB, TMDB and modern Python best practices.

## ✨ Features

IMPORTANT - This project is in active development. Bugs and glitches are expected. Join [reelnnUpdates](https://t.me/reelnnUpdates) for future updates
See all features -> [reelnn](https://github.com/rafsanbasunia/reelnn)

## 🔧 Configuration

### Environment Variables

#### Mandatory variables:
- `DATABASE_URL`: MongoDB connection string

- `API_ID`: Telegram API ID
- `API_HASH`: Telegram API hash
- `BOT_TOKEN`: Telegram bot token
- `OWNER_ID` : Your Telegram UserID.
- `TMDB_API_KEY`: The Movie Database API key
- `ADMIN_USERNAME` : Admin username for the content manager.
- `ADMIN_PASSWORD` : Admin password for the content manager.
- `AUTH_CHAT` : Replace with your actual auth chat ID. You can use multiple IDs separated by ( space ).
- `LOGS_CHAT` : Replace with your actual logs chat ID
- `POST_CHAT` : Replace with your actual post chat ID
- `SITE_SECRET` : Replace with your site secret key
- `TMDB_API_KEY` : Replace with your TMDB API key



#### Optional Variables
- `MULTI_TOKENS` = Add bot tokens to speed up downloading files via web. 

- `POST_UPDATES` =  Enable/disable auto-posting
- `USE_CAPTION` =  Use file caption vs filename
- `PORT`: Web server port (default: 8080)



### Prerequisites
- Python 3.12+
- All the requirements for `config.py`

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/rafsanbasunia/reelnn-backend.git
   cd reelnn-backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   Edit `config.py` and update the Mandatory and Optional variables.


4. **Run the application**
   ```bash
   python app.py
   ```
## 🚀 Deployment

### Docker Deployment
```bash
docker build -t reelnn-backend .
docker run -p 8080:8080 reelnn-backend
```
### Heroku Deployment
coming soon ...


## 🎯 Bot Commands

### User Commands
- `/start file_{token}` - Access specific media file

### Admin Commands
```
batch - /batch {start_message_link} {end_message_link} Batch process media files
del - /del {url} Delete content
post_updates - Toggle auto-posting
use_caption - Toogle filename vs caption
```

## ✨ Credits

This project incorporates code from several open-source projects:
- **TechZIndex** by TechShreyash
- **Surf-TG** by weebzone
- **libdrive** by libdrive

## License

[MIT](https://choosealicense.com/licenses/mit/)