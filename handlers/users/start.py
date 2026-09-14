"""Saytga kirish uchun kod berish.

Birinchi marta: raqam → yosh → kod.
Keyingi safar /start: kod darrov (raqam ham, yosh ham so'ralmaydi).
Yoshi chegaradan katta bo'lsa kod berilmaydi; qayta /start bosilsa yosh yana so'raladi.
"""

import io

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.builtin import CommandStart

from loader import bot, dp
from states.auth import AuthState
from utils.site_api import request_code


def contact_keyboard() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("📱 Raqamni yuborish", request_contact=True))
    return keyboard


def user_fields(user: types.User) -> dict:
    return {
        'telegram_id': user.id,
        'first_name': user.first_name or '',
        'last_name': user.last_name or '',
        'username': user.username or '',
    }


@dp.message_handler(CommandStart(), state='*')
async def bot_start(message: types.Message, state: FSMContext):
    await state.finish()

    ok, response = await request_code(**user_fields(message.from_user))
    await handle_response(message, ok, response)


@dp.message_handler(content_types=types.ContentType.CONTACT, state='*')
async def got_contact(message: types.Message, state: FSMContext):
    contact = message.contact

    if contact.user_id != message.from_user.id:
        await message.answer("O'zingizning raqamingizni yuboring 👇",
                             reply_markup=contact_keyboard())
        return

    await state.finish()

    ok, response = await request_code(
        **user_fields(message.from_user),
        phone=contact.phone_number or '',
        photo=await download_avatar(message.from_user.id),
    )
    await handle_response(message, ok, response)


@dp.message_handler(state=AuthState.waiting_age)
async def got_age(message: types.Message, state: FSMContext):
    text = (message.text or '').strip()

    if not text.isdigit():
        await message.answer("Yoshingizni faqat raqam bilan yozing. Masalan: <b>21</b>")
        return

    await state.finish()

    ok, response = await request_code(**user_fields(message.from_user), age=int(text))
    await handle_response(message, ok, response)


@dp.message_handler(state=AuthState.waiting_contact)
async def remind_contact(message: types.Message):
    await message.answer("Pastdagi tugmani bosing 👇", reply_markup=contact_keyboard())


async def handle_response(message: types.Message, ok: bool, response: dict):
    """Sayt javobiga qarab: kod beradi yoki keyingi savolni so'raydi."""
    if ok:
        await message.answer(
            f"<b>Kodingiz:</b>\n\n<code>{response['code']}</code>\n\n"
            "Saytga kiriting. Kod 5 daqiqa amal qiladi.\n"
            "Yangi kod kerak bo'lsa — /start bosing.",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        return

    error = response.get('error')

    if error == 'need_phone':
        await AuthState.waiting_contact.set()
        await message.answer(
            "Assalomu alaykum! Saytga kirish uchun raqamingizni yuboring 👇",
            reply_markup=contact_keyboard(),
        )
    elif error == 'need_age':
        await AuthState.waiting_age.set()
        await message.answer(
            "Rahmat! Endi yoshingizni yozing 👇\n\nMasalan: <b>21</b>",
            reply_markup=types.ReplyKeyboardRemove(),
        )
    elif error == 'bad_age':
        await AuthState.waiting_age.set()
        await message.answer("Yoshni to'g'ri yozing (7 dan 100 gacha). Masalan: <b>21</b>")
    elif error == 'age_limit':
        limit = response.get('limit', 30)
        # Yosh shu yerning o'zida qayta so'raladi; /start bosilsa ham shu savol chiqadi
        await AuthState.waiting_age.set()
        await message.answer(
            f"😔 Kechirasiz, bu saytga faqat <b>{limit} yoshgacha</b> bo'lgan yoshlar kira oladi.\n\n"
            "Yoshingizni noto'g'ri yozgan bo'lsangiz, qaytadan yozing 👇",
            reply_markup=types.ReplyKeyboardRemove(),
        )
    else:
        await message.answer(
            f"Xatolik: <code>{error or 'nomalum'}</code>\n"
            "Birozdan keyin qayta urinib ko'ring.",
            reply_markup=types.ReplyKeyboardRemove(),
        )


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
