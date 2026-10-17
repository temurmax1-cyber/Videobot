import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiohttp import web
import yt_dlp

# Token va sozlamalar
TOKEN = os.getenv("BOT_TOKEN", "SIZNING_BOT_TOKENINGIZ")
PORT = int(os.getenv("PORT", 8080))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Render uchun oddiy web-server (UptimeRobot 24/7 ishlashi uchun)
async def handle(request):
    return web.Response(text="Bot ishlayapti!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

# 1. /start komandasi
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Assalomu alaykum! 🎵\n\n"
        "Men media va musiqa yordamchisi botiman:\n"
        "• **Instagram, TikTok** havolalarini yuborsangiz — videoni yuklab beraman.\n"
        "• **Musiqa nomini yozsangiz** — YouTube'dan topib, audio ko'rinishida tashlab beraman."
    )

# 2. Havolalar yoki Musiqa nomini matn ko'rinishida qabul qilish
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: types.Message):
    text = message.text.strip()
    msg = await message.answer("🔍 Qidirilmoqda va yuklab olinmoqda, iltimos kuting...")

    try:
        # Agar matn havola bo'lmasa, uni musiqa nomi deb tushunib YouTube'dan qidiramiz
        if not text.startswith("http"):
            query = f"ytsearch1:{text}"
            ydl_opts = {
                'format': 'bestaudio/bestaudio',
                'outtmpl': 'downloads/%(id)s.%(ext)s',
                'noplaylist': True,
            }
            search_target = query
        else:
            search_target = text
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': 'downloads/%(id)s.%(ext)s',
                'noplaylist': True,
            }
            # Agar YouTube havolasi bo'lsa va cookies mavjud bo'lsa
            if "youtube.com" in text or "youtu.be" in text:
                if os.path.exists("cookies.txt"):
                    ydl_opts['cookiefile'] = 'cookies.txt'

        os.makedirs("downloads", exist_ok=True)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_target, download=True)
            if 'entries' in info:
                info = info['entries'][0]
            
            filename = ydl.prepare_filename(info)

        if os.path.exists(filename):
            file_size = os.path.getsize(filename) / (1024 * 1024) # MB da
            if file_size > 50:
                await msg.edit_text("❌ Fayl hajmi 50MB dan katta, Telegram cheklovi tufayli yubora olmayman.")
                os.remove(filename)
                return

            input_file = FSInputFile(filename)
            if not text.startswith("http"):
                await message.answer_audio(input_file, caption=f"🎵 Topilgan musiqa: {info.get('title', 'Nomaʼlum')}")
            else:
                await message.answer_video(input_file, caption="✅ Marhamat, video tayyor!")
            
            os.remove(filename)
            await msg.delete()
        else:
            await msg.edit_text("❌ Afsuski, hech narsa topilmadi yoki yuklab bo'lmadi.")

    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)}")

# Asosiy ishga tushirish funksiyasi
async def main():
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    
    # Web serverni fonda ishga tushiramiz (Render uchun)
    asyncio.create_task(start_web_server())
    
    # Botni ishga tushiramiz
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
