import os
import asyncio
import hashlib
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

TOKEN = "8597649397:AAGsC_TfivNXmJwNPMFjmMgGGUOcybSA5FI"

bot = Bot(token=TOKEN)
dp = Dispatcher()

url_cache = {}

def get_media_info(url):
    ydl_opts = {
        'noplaylist': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if 'entries' in info:
            info = info['entries'][0]
        return info

def download_media(url, download_type='video'):
    os.makedirs('downloads', exist_ok=True)
    ydl_opts = {
        'noplaylist': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'outtmpl': 'downloads/%(id)s.%(ext)s',
    }
    
    if download_type == 'audio':
        ydl_opts.update({'format': 'bestaudio/best'})
    else:
        ydl_opts.update({'format': 'best'})
        
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if 'entries' in info:
            info = info['entries'][0]
        filename = ydl.prepare_filename(info)
        return filename

@dp.message(F.text.startswith("http"))
async def link_handler(message: Message):
    url = message.text.strip()
    status_msg = await message.answer("🔍 **Ma'lumot tekshirilmoqda...**", parse_mode="Markdown")
    
    try:
        loop = asyncio.get_running_loop()
        info = await loop.run_in_executor(None, get_media_info, url)
        
        ext = info.get('ext', '')
        # Agar post rasm bo'lsa, to'g'ridan-to'g'ri yuklab yuboramiz
        if ext in ['jpg', 'jpeg', 'png', 'webp'] or (info.get('vcodec') == 'none' and ext in ['jpg', 'jpeg', 'png', 'webp']):
            await status_msg.edit_text("⏳ **Rasm yuklab olinmoqda...**", parse_mode="Markdown")
            file_path = await loop.run_in_executor(None, download_media, url, 'photo')
            
            bot_info = await bot.get_me()
            caption = (
                f"🤖 Bot nomi: {bot_info.first_name} (@{bot_info.username})\n"
                f"📌 Instagram va tiktokdan video, audio Yuklovchi bot"
            )
            
            file = FSInputFile(file_path)
            await message.answer_photo(file, caption=caption)
            
            if os.path.exists(file_path):
                os.remove(file_path)
            await status_msg.delete()
            return
            
        # Agar video bo'lsa, tugmalarni chiqaramiz
        h = hashlib.md5(url.encode()).hexdigest()[:8]
        url_cache[h] = url
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎬 Video yuklab olish", callback_data=f"video_{h}"),
                InlineKeyboardButton(text="🎵 Musiqa yuklash", callback_data=f"audio_{h}")
            ]
        ])
        
        await status_msg.edit_text(
            "🔗 **Havola qabul qilindi!**\n\nQaysi formatda yuklab olishni xohlaysiz?",
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
    
    if h not in url_cache:
        await callback.answer("❌ Havola eskirgan yoki topilmadi. Iltimos, havolani qaytadan yuboring.", show_alert=True)
        return
        
    url = url_cache[h]
    await callback.message.edit_text("⏳ **Yuklab olinmoqda, iltimos kuting...**", parse_mode="Markdown")
    
    try:
        loop = asyncio.get_running_loop()
        file_path = await loop.run_in_executor(None, download_media, url, download_type)
        
        await callback.message.edit_text("📤 **Telegramga yuborilmoqda...**", parse_mode="Markdown")
        
        bot_info = await bot.get_me()
        caption = (
            f"🤖 Bot nomi: {bot_info.first_name} (@{bot_info.username})\n"
            f"📌 Instagram va tiktokdan video, audio Yuklovchi bot"
        )
        
        file = FSInputFile(file_path)
        if download_type == 'audio':
            await callback.message.answer_audio(file, caption=caption)
        else:
            await callback.message.answer_video(file, caption=caption)
            
        if os.path.exists(file_path):
            os.remove(file_path)
        await callback.message.delete()
        
    except Exception as e:
        await callback.message.edit_text(f"❌ **Xatolik yuz berdi:**\n{e}", parse_mode="Markdown")

# Render uxlab qolmasligi uchun veb-server
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
    # Veb-server va botni bir vaqtda ishga tushiramiz
    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
