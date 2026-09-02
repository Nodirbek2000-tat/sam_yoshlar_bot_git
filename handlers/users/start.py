"""Saytga kirish uchun kod berish.

Foydalanuvchi raqamini yuboradi — bot darrov kod beradi. Tamom.
"""

import io

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.builtin import CommandStart

from data import config
from loader import bot, dp
from states.auth import AuthState
from utils.site_api import request_code


def contact_keyboard() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("📱 Raqamni yuborish", request_contact=True))
    return keyboard


@dp.message_handler(CommandStart(), state='*')
async def bot_start(message: types.Message, state: FSMContext):
    await state.finish()
    await AuthState.waiting_contact.set()
    await message.answer(
        "Raqamingizni yuboring 👇",
        reply_markup=contact_keyboard(),
    )


@dp.message_handler(content_types=types.ContentType.CONTACT, state='*')
async def got_contact(message: types.Message, state: FSMContext):
    contact = message.contact

    if contact.user_id != message.from_user.id:
        await message.answer("O'zingizning raqamingizni yuboring 👇",
                             reply_markup=contact_keyboard())
        return

    await state.finish()

    photo = await download_avatar(message.from_user.id)

    ok, response = await request_code(
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name or '',
        last_name=message.from_user.last_name or '',
        username=message.from_user.username or '',
        phone=contact.phone_number or '',
        photo=photo,
    )

    if ok:
        await message.answer(
            f"<b>Kodingiz:</b>\n\n<code>{response['code']}</code>\n\n"
            "Saytga kiriting. Kod 5 daqiqa amal qiladi.",
            reply_markup=types.ReplyKeyboardRemove(),
        )
    else:
        await message.answer(
            f"Xatolik: <code>{response.get('error', 'nomalum')}</code>\n"
            "Birozdan keyin qayta urinib ko'ring.",
            reply_markup=types.ReplyKeyboardRemove(),
        )


@dp.message_handler(state=AuthState.waiting_contact)
async def remind_contact(message: types.Message):
    await message.answer("Pastdagi tugmani bosing 👇", reply_markup=contact_keyboard())


async def download_avatar(user_id: int):
    """Telegram profil rasmini yuklab oladi (bo'lmasa None)."""
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
        if not photos.total_count:
            return None

        buffer = io.BytesIO()
        await bot.download_file_by_id(photos.photos[0][-1].file_id, destination=buffer)
        buffer.seek(0)
        return buffer.read()
    except Exception:
        return None
