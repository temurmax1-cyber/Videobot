import os
import asyncio
import hashlib
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

TOKEN = "8597649397:AAGsC_TfivNXmJwNPMFjmMgGGUOcybSA5FI"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# 1. SQLite Ma'lumotlar bazasini sozlash
def init_db():
    conn = sqlite3.connect('urls.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS links (hash TEXT PRIMARY KEY, url TEXT)''')
    conn.commit()
    conn.close()

def save_url(h, url):
    conn = sqlite3.connect('urls.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO links (hash, url) VALUES (?, ?)', (h, url))
    conn.commit()
    conn.close()

def get_url(h):
    conn = sqlite3.connect('urls.db')
    cursor = conn.cursor()
    cursor.execute('SELECT url FROM links WHERE hash = ?', (h,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

# 2. yt-dlp sozlamalari (Render uchun ffmpeg talab qilmaydigan format bilan)
def get_ydl_opts(download_type='video', download=False):
    opts = {
        'noplaylist': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'socket_timeout': 30,
        'quiet': True,
    }
    
    # Agar cookies.txt mavjud bo'lsa, YouTube cheklovlarini chetlab o'tish uchun qo'shamiz
    if os.path.exists('cookies.txt'):
        opts['cookiefile'] = 'cookies.txt'
        
    if download_type == 'audio':
        opts.update({'format': 'bestaudio/best'})
    else:
        # Render serverida ffmpeg yo'qligi sababli tayyor bitta mp4 fayl formatini tanlaymiz
        opts.update({'format': 'best[ext=mp4]/best'})
        
    if download:
        opts.update({'outtmpl': 'downloads/%(id)s.%(ext)s'})
        
    return opts

def get_media_info(url):
    ydl_opts = get_ydl_opts(download=False)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if 'entries' in info:
            info = info['entries'][0]
        return info

def download_media(url, download_type='video'):
    os.makedirs('downloads', exist_ok=True)
    ydl_opts = get_ydl_opts(download_type=download_type, download=True)
        
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if 'entries' in info:
            info = info['entries'][0]
        filename = ydl.prepare_filename(info)
        return filename

# 3. Xabarlarni qabul qilish va qayta ishlash
@dp.message(F.text.startswith("http"))
async def link_handler(message: Message):
    url = message.text.strip()
    status_msg = await message.answer("🔍 **Havola tekshirilmoqda...**", parse_mode="Markdown")
    
    try:
        loop = asyncio.get_running_loop()
        info = await loop.run_in_executor(None, get_media_info, url)
        
        ext = info.get('ext', '')
        # Rasm yoki postlar uchun
        if ext in ['jpg', 'jpeg', 'png', 'webp'] or (info.get('vcodec') == 'none' and ext in ['jpg', 'jpeg', 'png', 'webp']):
            await status_msg.edit_text("⏳ **Rasm yuklab olinmoqda...**", parse_mode="Markdown")
            file_path = await loop.run_in_executor(None, download_media, url, 'photo')
            
            bot_info = await bot.get_me()
            caption = f"🤖 Bot: @{bot_info.username}\n📌 Universal Media Yuklovchi"
            
            file = FSInputFile(file_path)
            await message.answer_photo(file, caption=caption)
            
            if os.path.exists(file_path):
                os.remove(file_path)
            await status_msg.delete()
            return
            
        # Video va boshqa media havolalari uchun
        h = hashlib.md5(url.encode()).hexdigest()[:8]
        save_url(h, url)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎬 Video yuklab olish", callback_data=f"video_{h}"),
                InlineKeyboardButton(text="🎵 Musiqa yuklash", callback_data=f"audio_{h}")
            ]
        ])
        
        await status_msg.edit_text(
            "🔗 **Havola muvaffaqiyatli qabul qilindi!**\n\nQaysi formatda yuklab olishni xohlaysiz?",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Xatolik yuz berdi:**\n{e}", parse_mode="Markdown")

@dp.callback_query(F.data.regexp(r"^(video|audio)_(.+)"))
async def callback_handler(callback: CallbackQuery):
    data_parts = callback.data.split("_", 1)
    download_type = data_parts[0]
    h = data_parts[1]
    
    url = get_url(h)
    if not url:
        await callback.answer("❌ Havola topilmadi yoki eskirgan. Iltimos, havolani qaytadan yuboring.", show_alert=True)
        return
        
    await callback.message.edit_text("⏳ **Yuklab olinmoqda, iltimos kuting...**", parse_mode="Markdown")
    
    try:
        loop = asyncio.get_running_loop()
        file_path = await loop.run_in_executor(None, download_media, url, download_type)
        
        await callback.message.edit_text("📤 **Telegramga yuborilmoqda...**", parse_mode="Markdown")
        
        bot_info = await bot.get_me()
        caption = f"🤖 Bot: @{bot_info.username}\n📌 Universal Media Yuklovchi"
        
        file = FSInputFile(file_path)
        if download_type == 'audio':
            await callback.message.answer_audio(file, caption=caption)
        else:
            await callback.message.answer_video(file, caption=caption)
            
        if os.path.exists(file_path):
            os.remove(file_path)
        await callback.message.delete()
        
    except Exception as e:
        await callback.message.edit_text(f"❌ **Yuklab olishda xatolik:**\n{e}", parse_mode="Markdown")

# 4. Render 24/7 ishlab turishi uchun web-server
async def handle_ping(request):
    return web.Response(text="Bot is active and running 24/7!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    init_db()
    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
