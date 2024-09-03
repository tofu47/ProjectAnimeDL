import os
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp as youtube_dl
from urllib.parse import urlparse, parse_qs
from config import API_ID, API_HASH, BOT_TOKEN, DOWNLOAD_DIR

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inisialisasi bot
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Notifikasi saat bot dijalankan
print("Bot sedang dijalankan...")

def is_valid_youtube_url(url):
    parsed_url = urlparse(url)
    if parsed_url.netloc in ['www.youtube.com', 'youtube.com', 'youtu.be']:
        if parsed_url.path == '/watch':
            return 'v' in parse_qs(parsed_url.query)
        elif parsed_url.path.startswith('/shorts/'):
            return True
        elif parsed_url.netloc == 'youtu.be':
            return len(parsed_url.path) > 1
    return False

@app.on_message(filters.command(["start", "help"]))
async def start_command(client, message):
    await message.reply("Selamat datang! Kirim link YouTube untuk mengunduh video.")

@app.on_message(filters.text & ~filters.command(["start", "help"]))
async def handle_youtube_link(client, message):
    if is_valid_youtube_url(message.text):
        await get_video_info(message)
    else:
        await message.reply("Mohon kirim link YouTube yang valid.")

async def get_video_info(message):
    try:
        with youtube_dl.YoutubeDL({'format': 'bestaudio/best'}) as ydl:
            info = ydl.extract_info(message.text, download=False)
            formats = info['formats']
            
            # Filter format video, hanya ambil resolusi 144p ke atas, dan urutkan
            video_formats = [f for f in formats if f.get('height') is not None and f['height'] >= 144]
            video_formats.sort(key=lambda x: (x['height'], x.get('fps', 0)))
            
            # Ambil resolusi maksimal
            max_resolution = f"{video_formats[-1]['height']}p" if video_formats else "Unknown"
            
            # Buat tombol untuk setiap resolusi unik yang tersedia
            buttons = []
            seen_resolutions = set()
            for format in video_formats:
                resolution = f"{format['height']}p"
                if resolution not in seen_resolutions:
                    seen_resolutions.add(resolution)
                    buttons.append([InlineKeyboardButton(
                        f"{resolution} ({format.get('fps', 'N/A')}fps)",
                        callback_data=f"dl_{format['format_id']}_{message.id}"
                    )])
            
            # Balik urutan tombol agar resolusi tertinggi muncul di atas
            buttons.reverse()
            
            reply_markup = InlineKeyboardMarkup(buttons)
            await message.reply(
                f"Resolusi tersedia: 144p - {max_resolution}\n"
                "Pilih resolusi yang Anda inginkan:",
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error saat mengambil info video: {e}")
        await message.reply("Terjadi kesalahan saat memproses video. Mohon coba lagi.")

@app.on_callback_query()
async def handle_resolution_choice(client, callback_query):
    data = callback_query.data.split('_')
    if data[0] == 'dl':
        format_id = data[1]
        original_message_id = int(data[2])
        original_message = await app.get_messages(callback_query.message.chat.id, original_message_id)
        
        await callback_query.message.edit_text("Memulai unduhan...")
        await download_video(original_message, format_id, callback_query.message)

async def download_video(original_message, format_id, status_message):
    try:
        ydl_opts = {
            'format': format_id,
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            'progress_hooks': [lambda d: download_progress_hook(d, status_message)]
        }
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(original_message.text, download=True)
            video_file = ydl.prepare_filename(info_dict)
        
        await status_message.edit_text("Unduhan selesai. Memulai proses upload ke Telegram...")
        
        await original_message.reply_video(
            video_file,
            progress=upload_progress,
            progress_args=(status_message,)
        )
        
        os.remove(video_file)
        await status_message.edit_text("Proses selesai. Video telah diunggah.")
        
    except Exception as e:
        logger.error(f"Kesalahan saat mengunduh/upload video: {e}")
        await status_message.edit_text(f"Terjadi kesalahan: {e}")

async def download_progress_hook(d, status_message):
    if d['status'] == 'downloading':
        percent = d['_percent_str']
        speed = d['_speed_str']
        eta = d['_eta_str']
        await status_message.edit_text(f"Mengunduh: {percent} selesai\nKecepatan: {speed}\nPerkiraan waktu: {eta}")

async def upload_progress(current, total, status_message):
    percent = f"{current * 100 / total:.1f}%"
    await status_message.edit_text(f"Mengupload: {percent} selesai")

# Menjalankan bot
if __name__ == "__main__":
    print("Bot sedang mencoba terhubung ke Telegram...")
    app.run()
    print("Bot telah berhenti.")