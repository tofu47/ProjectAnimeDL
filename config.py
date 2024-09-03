import os
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Konfigurasi API dan Token Bot
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# API KrakenFiles
KRAKEN_API_KEY = os.environ.get("KRAKEN_API_KEY")

# Direktori untuk menyimpan file yang diunduh
DOWNLOAD_DIR = "./DOWNLOADS"
