import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiohttp import web
import yt_dlp

# Sizning bot tokeningiz
TOKEN = "8597649397:AAGsC_TfivNXmJwNPMFjmMgGGUOcybSA5FI"
PORT = int(os.getenv("PORT", 8080))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Foydalanuvchining oxirgi yuborgan havolasini saqlash uchun lug'at
user_links = {}

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
        "• Videolar ostidagi tugma orqali uning **audiosini** ham alohida yuklab olishingiz mumkin."
    )

# 2. Havolalarni qabul qilish
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: types.Message):
    text = message.text.strip()
    msg = await message.answer("🔍 Qidirilmoqda va yuklab olinmoqda, iltimos kuting...")

    try:
        ydl_opts = {
            'noplaylist': True,
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'format': 'best[ext=mp4]/best',
        }

        if "youtube.com" in text or "youtu.be" in text:
            if os.path.exists("cookies.txt"):
                ydl_opts['cookiefile'] = 'cookies.txt'

        os.makedirs("downloads", exist_ok=True)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(text, download=True)
            if 'entries' in info:
                info = info['entries'][0]
            
            filename = ydl.prepare_filename(info)

        if os.path.exists(filename):
            file_size = os.path.getsize(filename) / (1024 * 1024) # MB da
            if file_size > 50:
                await msg.edit_text("❌ Fayl hajmi 50MB dan katta, Telegram cheklovi tufayli yubora olmayman.")
                os.remove(filename)
                return

            # Foydalanuvchi uchun havolani saqlab qo'yamiz (audio tugmasi ishlashi uchun)
            user_links[message.from_user.id] = text

            input_file = FSInputFile(filename)
            caption = (
                "✅ Marhamat, video tayyor!\n\n"
                "📥 Yukla botdan yuklab olindi\n"
                "🤖 Bot manzili: @Yukla100_bot"
            )

            # Audio yuklab olish uchun tugma
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎵 Audio yuklab olish", callback_data="download_audio")]
            ])

            await message.answer_video(input_file, caption=caption, reply_markup=keyboard)
            
            os.remove(filename)
            await msg.delete()
        else:
            await msg.edit_text("❌ Afsuski, hech narsa topilmadi yoki yuklab bo'lmadi.")

    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)}")

# 3. Audio yuklab olish tugmasi bosilganda ishlaydigan qism
@dp.callback_query(F.data == "download_audio")
async def callback_download_audio(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_links:
        await callback.answer("❌ Havola topilmadi, iltimos qaytadan havola yuboring.", show_alert=True)
        return
    
    link = user_links[user_id]
    msg = await callback.message.answer("🔍 Audio ajratib olinmoqda, iltimos kuting...")
    
    try:
        ydl_opts = {
            'format': 'bestaudio/bestaudio',
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'noplaylist': True,
        }
        if "youtube.com" in link or "youtu.be" in link:
            if os.path.exists("cookies.txt"):
                ydl_opts['cookiefile'] = 'cookies.txt'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            if 'entries' in info:
                info = info['entries'][0]
            filename = ydl.prepare_filename(info)

        if os.path.exists(filename):
            input_file = FSInputFile(filename)
            audio_caption = (
                "🎵 Audio muvaffaqiyatli yuklab olindi!\n\n"
                "📥 Yukla botdan yuklab olindi\n"
                "🤖 Bot manzili: @Yukla100_bot"
            )
            await callback.message.answer_audio(input_file, caption=audio_caption)
            os.remove(filename)
            await msg.delete()
        else:
            await msg.edit_text("❌ Audioni yuklab bo'lmadi.")
    except Exception as e:
        logging.error(f"Audio xatolik: {e}")
        await msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)}")
    
    await callback.answer()

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
