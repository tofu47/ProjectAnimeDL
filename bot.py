import os
import logging
import zipfile
import shutil
import rarfile
import gdown
import re
import asyncio
from telegram import Message
from urllib.parse import urlparse, parse_qs
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
import yt_dlp as youtube_dl
import time
import subprocess  # Tambahkan pustaka subprocess
from config import API_ID, API_HASH, BOT_TOKEN, DOWNLOAD_DIR

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inisialisasi bot
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Notifikasi saat bot dijalankan
print("Bot sedang dijalankan...")

# Variabel untuk menyimpan mode dan resolusi yang dipilih oleh pengguna
user_selections = {}
user_modes = {}

@app.on_message(filters.command(["start", "help"]))
async def start_command(client, message):
    buttons = [
        [InlineKeyboardButton("YouTube", callback_data="mode_youtube")],
        [InlineKeyboardButton("Google Drive", callback_data="mode_drive")],
        [InlineKeyboardButton("Convert link", callback_data="convert_link")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply("Selamat datang! Pilih mode yang Anda inginkan:", reply_markup=reply_markup)

@app.on_callback_query(filters.regex(r'^mode_'))
async def handle_mode_selection(client, callback_query):
    mode = callback_query.data.split('_')[1]
    user_modes[callback_query.from_user.id] = mode
    logger.info(f"Mode dipilih oleh {callback_query.from_user.id}: {mode}")
    
    # Kirim respons cepat kepada pengguna untuk memberitahukan mode yang dipilih
    await callback_query.answer(f"Mode {mode} dipilih!")
    
    if mode == "youtube":
        # Menampilkan opsi resolusi jika mode YouTube dipilih
        buttons = [
            [InlineKeyboardButton("144p", callback_data="resolution_144")],
            [InlineKeyboardButton("360p", callback_data="resolution_360")],
            [InlineKeyboardButton("480p", callback_data="resolution_480")],
            [InlineKeyboardButton("720p", callback_data="resolution_720")],
            [InlineKeyboardButton("1080p", callback_data="resolution_1080")]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await callback_query.message.reply("Pilih resolusi yang Anda inginkan:", reply_markup=reply_markup)
    else:
        # Mode Google Drive dipilih, minta pengguna mengirimkan link Google Drive
        await callback_query.message.reply(f"Mode {mode} telah dipilih. Kirimkan link Google Drive untuk memproses.")
###logger 
@app.on_callback_query(filters.regex(r'^resolution_'))
async def handle_resolution_selection(client, callback_query):
    try:
        resolution = callback_query.data.split('_')[1]
        user_selections[callback_query.from_user.id] = resolution
        logger.info(f"Resolusi dipilih oleh {callback_query.from_user.id}: {resolution}")

        # Give user choose resolution
        await callback_query.answer(f"Resolusi {resolution} dipilih!")

        # Give instruction to user
        await callback_query.message.reply(f"Resolusi {resolution} telah dipilih. Kirimkan link YouTube untuk mengunduh video atau playlist.")
    except Exception as e:
        logger.error(f"Error handling resolution selection: {e}")

##Download percent logger
async def download_progress_hook(d, status_message):
    global last_download_percent
    if d['status'] == 'downloading':
        percent = float(d['_percent_str'].strip('%'))
        if percent - last_download_percent >= 15: 
            last_download_percent = percent
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            await status_message.edit_text(f"Mengunduh: {percent:.1f}% selesai\nKecepatan: {speed}\nPerkiraan waktu: {eta}")




@app.on_callback_query(filters.regex(r'^convert_link$'))
async def handle_convert_link(client, callback_query):
    user_id = callback_query.from_user.id
    user_modes[user_id] = "convert_link" 
    await callback_query.message.reply("Silakan kirimkan link yang ingin Anda konversi.")


@app.on_message(filters.text & ~filters.command(["start", "help"]))
async def handle_link(client, message):
    user_id = message.from_user.id
    mode = user_modes.get(user_id)
    
    if mode == "youtube":
        resolution = user_selections.get(user_id)
        if resolution is None:
            await message.reply("Silakan pilih resolusi terlebih dahulu dengan menggunakan tombol resolusi.")
            return
        
        if not is_valid_youtube_url(message.text):
            await message.reply("Mohon kirim link YouTube yang valid.")
            return

        try:
            await download_and_upload_youtube(message, resolution)
        except FloodWait as e:
            logger.warning(f"Terkena FloodWait, menunggu selama {e.x} detik...")
            await asyncio.sleep(e.x)
            await handle_link(client, message) 
    
    elif mode == "drive":
        if not is_valid_google_drive_url(message.text):
            await message.reply("Mohon kirim link Google Drive yang valid.")
            return

        try:
            await download_and_extract_drive(message)
        except FloodWait as e:
            logger.warning(f"Terkena FloodWait, menunggu selama {e.x} detik...")
            await asyncio.sleep(e.x)
            await handle_link(client, message) 

    # to handle convert link
    elif mode == "convert_link":
        await convert_and_reply_link(message)
    
    else:
        await message.reply("Silakan pilih mode terlebih dahulu dengan menggunakan /start.")

async def convert_and_reply_link(message):
    try:
        # To run convert.py script
        result = subprocess.run(['python3', 'convert.py', message.text], capture_output=True, text=True)
        
        # Dapatkan hasil konversi dari output
        output = result.stdout.strip()
        
        if result.returncode == 0 and output:
            await message.reply(f"Link yang telah dikonversi: {output}")
        else:
            await message.reply("Terjadi kesalahan saat mengonversi link. Pastikan link yang diberikan valid.")
    
    except Exception as e:
        logger.error(f"Kesalahan saat menjalankan konversi link: {e}")
        await message.reply(f"Terjadi kesalahan: {e}")

def is_valid_youtube_url(url):
    parsed_url = urlparse(url)
    if parsed_url.netloc in ['www.youtube.com', 'youtube.com', 'youtu.be']:
        if parsed_url.path == '/watch':
            return 'v' in parse_qs(parsed_url.query)
        elif parsed_url.path.startswith('/shorts/'):
            return True
        elif parsed_url.path == '/playlist':  # For checking playlist
            return 'list' in parse_qs(parsed_url.query)
        elif parsed_url.netloc == 'youtu.be':
            return len(parsed_url.path) > 1
    return False

def is_valid_google_drive_url(url):
    parsed_url = urlparse(url)
    return "drive.google.com" in parsed_url.netloc


# yt-dlp config
async def download_and_upload_youtube(message, resolution):
    try:
        status_message = await message.reply("Memulai unduhan...")
        
        ydl_opts = {
            'format': f'bestvideo[height<={resolution}]+bestaudio/best',
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            'noplaylist': True,  # Hanya mengunduh video tunggal
            'progress_hooks': [lambda d: asyncio.ensure_future(download_progress_hook(d, status_message))],
            'cookiefile': 'cookies.txt'
        }
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(message.text, download=True)
            if 'entries' in info_dict:
                for entry in info_dict['entries']:
                    video_file = ydl.prepare_filename(entry)
                    await status_message.edit_text(f"Unduhan {entry['title']} selesai. Menunggu sebelum proses upload...")
                    await asyncio.sleep(5) # Pause every 5s before uploading
                    await status_message.edit_text(f"Memulai proses upload {entry['title']} ke Telegram...")
                    await message.reply_video(
                        video_file,
                        progress=upload_progress,
                        progress_args=(status_message,)
                    )
                    os.remove(video_file)
            else:
                video_file = ydl.prepare_filename(info_dict)
                await status_message.edit_text("Unduhan selesai. Menunggu sebelum proses upload...")
                await asyncio.sleep(10)  # Jeda selama 10 detik sebelum upload
                await status_message.edit_text("Memulai proses upload ke Telegram...")
                await message.reply_video(
                    video_file,
                    progress=upload_progress,
                    progress_args=(status_message,)
                )
                os.remove(video_file)
        
        await status_message.edit_text("Proses selesai. Video telah diunggah.")
        
    except FloodWait as e:
        wait_time = e.x
        logger.warning(f"Terkena FloodWait, menunggu selama {wait_time} detik...")
        await asyncio.sleep(wait_time) 
        await download_and_upload_youtube(message, resolution)
    except Exception as e:
        logger.error(f"Kesalahan saat mengunduh/upload video: {e}")
        await status_message.edit_text(f"Terjadi kesalahan: {e}")


last_upload_percent = 0

async def upload_progress(current, total, status_message):
    global last_upload_percent
    percent = (current * 100) / total
    if percent - last_upload_percent >= 15:  # Update every 15%
        last_upload_percent = percent
        await status_message.edit_text(f"Mengunggah: {percent:.1f}% selesai")


def extract_drive_file_id(url):
    parsed_url = urlparse(url)
    if parsed_url.netloc == 'drive.google.com':
        # Cek apakah URL mengandung parameter 'id'
        query_params = parse_qs(parsed_url.query)
        if 'id' in query_params:
            return query_params['id'][0]
        # Cek apakah URL mengandung ID file langsung di path
        path_parts = parsed_url.path.split('/')
        if len(path_parts) > 2 and path_parts[1] == 'file':
            return path_parts[2]
    return None

# Download GDrive
async def download_and_extract_drive(message: Message):
    try:
        status_message = await message.reply("Memulai unduhan dari Google Drive...")

        # Ekstrak ID file from URL
        file_id = extract_drive_file_id(message.text)
        if not file_id:
            await status_message.edit_text("ID file Google Drive tidak valid.")
            return

        # URL unduhan Google Drive
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

        # Make sure if the download folder exist, it not make it
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        # Gunakan gdown untuk mengunduh file dan dapatkan nama file dari hasil unduhan
        # Make gdown to download file and take the name it
        output = os.path.join(DOWNLOAD_DIR, '') 
        downloaded_file = gdown.download(download_url, output=output, quiet=False)

        if not downloaded_file:
            await status_message.edit_text("Gagal mengunduh file dari Google Drive.")
            return

        # To check if the file zip or not, if not .zip directly upload the file to telegram
        extracted_folder = os.path.join(DOWNLOAD_DIR, os.path.splitext(os.path.basename(downloaded_file))[0])

        if zipfile.is_zipfile(downloaded_file):
            os.makedirs(extracted_folder, exist_ok=True)
            with zipfile.ZipFile(downloaded_file, 'r') as zip_ref:
                zip_ref.extractall(extracted_folder)
            os.remove(downloaded_file)
        elif downloaded_file.lower().endswith('.rar'):
            logger.info("File RAR terdeteksi, akan mengextract.")
            try:
                # using rarfile to extract the .rar
                os.makedirs(extracted_folder, exist_ok=True)
                with rarfile.RarFile(downloaded_file) as rar:
                    rar.extractall(extracted_folder)
                os.remove(downloaded_file)
            except rarfile.RarCannotExec as e:
                await status_message.edit_text(f"Kesalahan saat mengekstrak file RAR: {e}")
                return
        else:
            extracted_folder = downloaded_file 

        await status_message.edit_text(f"Unduhan dan ekstraksi selesai. Mengunggah file ke Telegram...")

        # Upload file and extract to telegram
        if os.path.isdir(extracted_folder):
            for root, dirs, files in os.walk(extracted_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    await message.reply_document(
                        file_path,
                        progress=upload_progress,
                        progress_args=(status_message,)
                    )
        else:
            await message.reply_document(
                extracted_folder,
                progress=upload_progress,
                progress_args=(status_message,)
            )

        await status_message.edit_text("Proses selesai. Semua file telah diunggah.")

        # for the delete the file/folder after upload
        if os.path.isdir(extracted_folder):
            shutil.rmtree(extracted_folder)
        else:
            os.remove(extracted_folder)

    except FloodWait as e:
        wait_time = e.x
        logger.warning(f"Terkena FloodWait, menunggu selama {wait_time} detik...")
        await asyncio.sleep(wait_time)
        # Pause for 5s before upload the file
        await asyncio.sleep(5)
        await download_and_extract_drive(message) 
    except Exception as e:
        logger.error(f"Kesalahan saat mengunduh/mengekstrak file dari Google Drive: {e}")
        await status_message.edit_text(f"Terjadi kesalahan: {e}")
# Ping The Bot        
async def keep_alive():
    while True:
        logger.info("Ping server untuk menjaga sesi tetap hidup.")
        await asyncio.sleep(300)  # Pause every 5 minutes (300 second)

# Run bot
if __name__ == "__main__":
    print("Bot sedang mencoba terhubung ke Telegram...")
    loop = asyncio.get_event_loop()
    loop.create_task(keep_alive())  # To Keep Alive the bot
    app.run()
    print("Bot telah berhenti.")
