import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
import yt_dlp

TOKEN = "8597649397:AAGsC_TfivNXmJwNPMFjmMgGGUOcybSA5FI"

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()
bot = Bot(token=TOKEN)

def download_media(url: str, download_type: str = "video"):
    ydl_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'format': 'bestaudio/best' if download_type == 'audio' else 'bestvideo+bestaudio/best',
    }
    
    if download_type == 'audio':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if download_type == 'audio':
            filename = os.path.splitext(filename)[0] + ".mp3"
        return filename, info.get('title', 'Media')

@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "Assalomu alaykum! 👋\n\n"
        "Menga YouTube, TikTok, Instagram, Snapchat yoki Likee havolalarini yuboring, "
        "men sizga videoni yuklab beraman!"
    )

@dp.message()
async def handle_url(message: Message):
    url = message.text.strip()
    supported_domains = ["youtube.com", "youtu.be", "tiktok.com", "instagram.com", "snapchat.com", "likee.video"]
    
    if not any(domain in url for domain in supported_domains):
        await message.answer("Iltimos, qo'llab-quvvatlanadigan tarmoqlardan birining havolasini yuboring!")
        return

    processing_msg = await message.answer("⏳ Media yuklab olinmoqda, biroz kuting...")

    try:
        file_path, title = download_media(url, download_type="video")
        file = types.FSInputFile(file_path)
        await message.answer_video(video=file, caption=f"📥 {title}")
        
        os.remove(file_path)
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
        except:
            pass

async def main():
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
