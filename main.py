import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

TOKEN = "8597649397:AAGsC_TfivNXmJwNPMFjmMgGGUOcybSA5FI"

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_links = {}

def download_media(url, download_type='video'):
    os.makedirs('downloads', exist_ok=True)
    
    # YouTube cheklovlarini chetlab o'tish uchun qo'shimcha sozlamalar
    ydl_opts = {
        'noplaylist': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    }
    
    if download_type == 'audio':
        ydl_opts.update({
            'format': 'bestaudio/best',
        })
    else:
        ydl_opts.update({
            'format': 'best[ext=mp4]/best/bestvideo+bestaudio',
        })
        
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return filename

@dp.message(F.text.startswith("http"))
async def link_handler(message: Message):
    url = message.text.strip()
    user_links[message.from_user.id] = url
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Video yuklab olish", callback_data="dl_video"),
            InlineKeyboardButton(text="🎵 Musiqa (Audio) yuklab olish", callback_data="dl_audio")
        ]
    ])
    
    await message.answer(
        "🔗 **Havola qabul qilindi!**\n\nQaysi formatda yuklab olishni xohlaysiz?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.in_({"dl_video", "dl_audio"}))
async def callback_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_links:
        await callback.answer("❌ Havola topilmadi yoki eskirgan. Iltimos, havolani qaytadan yuboring.", show_alert=True)
        return
        
    url = user_links[user_id]
    download_type = 'audio' if callback.data == "dl_audio" else 'video'
    
    await callback.message.edit_text("⏳ **Yuklab olinmoqda, iltimos kuting...**", parse_mode="Markdown")
    
    try:
        loop = asyncio.get_running_loop()
        file_path = await loop.run_in_executor(None, download_media, url, download_type)
        
        await callback.message.edit_text("📤 **Telegramga yuborilmoqda...**", parse_mode="Markdown")
        
        file = FSInputFile(file_path)
        if download_type == 'audio':
            await callback.message.answer_audio(file)
        else:
            await callback.message.answer_video(file)
            
        os.remove(file_path)
        await callback.message.delete()
        
    except Exception as e:
        await callback.message.edit_text(f"❌ **Xatolik yuz berdi:**\n{e}", parse_mode="Markdown")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
