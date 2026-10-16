import os
import asyncio
import hashlib
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

TOKEN = "8597649397:AAGsC_TfivNXmJwNPMFjmMgGGUOcybSA5FI"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Har bir havola uchun noyob xotira (adashib ketishning oldini oladi)
url_cache = {}

def download_media(url, download_type='video'):
    os.makedirs('downloads', exist_ok=True)
    
    ydl_opts = {
        'noplaylist': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        }
    }
    
    if download_type == 'audio':
        ydl_opts.update({
            'format': 'bestaudio/best',
        })
    elif download_type == 'photo':
        ydl_opts.update({
            'format': 'best',
        })
    else:
        ydl_opts.update({
            'format': 'best[ext=mp4]/best/bestvideo+bestaudio',
        })
        
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if 'entries' in info:
            info = info['entries'][0]
        filename = ydl.prepare_filename(info)
        return filename

@dp.message(F.text.startswith("http"))
async def link_handler(message: Message):
    url = message.text.strip()
    
    # Havola uchun noyob kalit (hash) yaratamiz
    h = hashlib.md5(url.encode()).hexdigest()[:8]
    url_cache[h] = url
    
    # 3 ta tugma
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Video yuklab olish", callback_data=f"video_{h}"),
            InlineKeyboardButton(text="🎵 Musiqa yuklash", callback_data=f"audio_{h}")
        ],
        [
            InlineKeyboardButton(text="🖼 Rasmni yuklash", callback_data=f"photo_{h}")
        ]
    ])
    
    await message.answer(
        "🔗 **Havola qabul qilindi!**\n\nQaysi formatda yuklab olishni xohlaysiz?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.regexp(r"^(video|audio|photo)_(.+)"))
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
        
        # Bot ma'lumotlarini olamiz
        bot_info = await bot.get_me()
        
        # Talab qilingan matn
        caption = (
            f"🤖 Bot nomi: {bot_info.first_name} (@{bot_info.username})\n"
            f"📌 Instagram va tiktokdan video, audio Yuklovchi bot"
        )
        
        file = FSInputFile(file_path)
        if download_type == 'audio':
            await callback.message.answer_audio(file, caption=caption)
        elif download_type == 'photo':
            await callback.message.answer_photo(file, caption=caption)
        else:
            await callback.message.answer_video(file, caption=caption)
            
        if os.path.exists(file_path):
            os.remove(file_path)
        await callback.message.delete()
        
    except Exception as e:
        await callback.message.edit_text(f"❌ **Xatolik yuz berdi:**\n{e}", parse_mode="Markdown")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
