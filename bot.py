import os
import logging
from pyrogram import Client
import yt_dlp as youtube_dl
from config import API_ID, API_HASH, BOT_TOKEN, DOWNLOAD_DIR

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inisialisasi bot
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Notifikasi saat bot dijalankan
print("Bot sedang dijalankan...")

@app.on_message()
async def handle_message(client, message):
    # Log setiap pesan yang diterima oleh bot
    logger.info(f"Pesan diterima dari {message.from_user.id}: {message.text}")
    
    if message.text:
        if message.text == "/start":
            await message.reply("Halo! Selamat datang di bot Telegram saya. Ketik /help untuk melihat daftar perintah.")
        elif message.text == "/help":
            await message.reply("Perintah yang tersedia:\n/start: Mulai bot\n/help: Tampilkan bantuan\n/about: Tentang bot\n/download: Unduh video YouTube")
        elif message.text == "/about":
            await message.reply("Ini adalah bot Telegram sederhana.")
        elif message.text.startswith("https://www.youtube.com/"):
            try:
                # Konfigurasi unduhan video
                ydl_opts = {
                    'format': 'best',
                    'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')
                }
                # Pastikan direktori download ada
                os.makedirs(DOWNLOAD_DIR, exist_ok=True)

                # Proses unduhan
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(message.text, download=True)
                    video_file = ydl.prepare_filename(info_dict)
                    await message.reply_video(video_file)
            except Exception as e:
                logger.error(f"Kesalahan saat mengunduh video: {e}")
                await message.reply(f"Terjadi kesalahan: {e}")

@app.on_callback_query()
async def handle_callback_query(client, callback_query):
    # Log setiap callback query yang diterima
    logger.info(f"User {callback_query.from_user.id} menekan tombol dengan data: {callback_query.data}")
    
    if callback_query.data == "press":
        await callback_query.message.reply("Kamu menekan tombol!")

# Menjalankan bot dan menampilkan notifikasi saat terhubung
if __name__ == "__main__":
    print("Bot sedang mencoba terhubung ke Telegram...")
    app.run()
    print("Bot telah berhenti.")
