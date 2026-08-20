import os
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not API_ID or not API_HASH or not BOT_TOKEN:
    print("Missing API_ID, API_HASH, or BOT_TOKEN in environment or .env file")
    exit(1)

API_ID = int(API_ID)

DB_PATH = "users.db"
SESSIONS_DIR = "sessions"
