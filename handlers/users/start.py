"""Saytga kirish uchun kod berish.

Oqim: majburiy kanallarga obuna → raqam (birinchi marta) → yosh → kod.
Keyingi safar /start bosilsa kod darrov beriladi.
"""

import io

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.builtin import CommandStart
from aiogram.utils.exceptions import TelegramAPIError

from keyboards.inline.admin import subscribe_menu
from loader import bot, dp
from states.auth import AuthState
from utils import site_api

#: Obuna bo'lmagan hisoblarning holati
LEFT = ('left', 'kicked')


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


# --------------------------------------------------------------------------
# Majburiy obuna
# --------------------------------------------------------------------------

async def check_subscription(user_id):
    """(barcha kanallar, obuna bo'linmaganlari).

    Bot kanalda admin bo'lmasa a'zolikni tekshira olmaydi — bunday kanal
    talab qilinmaydi, odam ushlanib qolmasin.
    """
    channels = await site_api.get_channels()
    missing = []

    for channel in channels:
        try:
            member = await bot.get_chat_member(channel['chat_id'], user_id)
        except TelegramAPIError:
            continue
        if member.status in LEFT:
            missing.append(channel)

    return channels, missing


async def ask_subscription(chat_id, missing):
    await bot.send_message(
        chat_id,
        "📢 Botdan foydalanish uchun quyidagi kanal(lar)ga obuna bo'ling:\n\n"
        "Obuna bo'lgach — <b>✅ Tekshirish</b> tugmasini bosing.",
        reply_markup=subscribe_menu(missing),
    )


async def passed_gate(user: types.User, chat_id) -> bool:
    """Obuna talabi bajarilganmi. Bajarilmasa — havolalarni chiqaradi."""
    channels, missing = await check_subscription(user.id)

    if missing:
        await ask_subscription(chat_id, missing)
        return False

    if channels:
        await site_api.record_joins(user.id, [item['chat_id'] for item in channels])
    return True


# --------------------------------------------------------------------------
# Kirish
# --------------------------------------------------------------------------

@dp.message_handler(CommandStart(), state='*')
async def bot_start(message: types.Message, state: FSMContext):
    await state.finish()

    if not await passed_gate(message.from_user, message.chat.id):
        return

    ok, response = await site_api.request_code(**user_fields(message.from_user))
    await respond(message.chat.id, ok, response)


@dp.callback_query_handler(lambda call: call.data == 'sub:check', state='*')
async def subscription_checked(call: types.CallbackQuery, state: FSMContext):
    _channels, missing = await check_subscription(call.from_user.id)

    if missing:
        await call.answer("Hali hammasiga obuna bo'lmadingiz", show_alert=True)
        return

    await call.answer("Rahmat! ✅")
    await call.message.edit_reply_markup()
    await state.finish()

    if not await passed_gate(call.from_user, call.message.chat.id):
        return

    ok, response = await site_api.request_code(**user_fields(call.from_user))
    await respond(call.message.chat.id, ok, response)


@dp.message_handler(content_types=types.ContentType.CONTACT, state='*')
async def got_contact(message: types.Message, state: FSMContext):
    contact = message.contact

    if contact.user_id != message.from_user.id:
        await message.answer("O'zingizning raqamingizni yuboring 👇",
                             reply_markup=contact_keyboard())
        return

    await state.finish()

    ok, response = await site_api.request_code(
        **user_fields(message.from_user),
        phone=contact.phone_number or '',
        photo=await download_avatar(message.from_user.id),
    )
    await respond(message.chat.id, ok, response)


@dp.message_handler(state=AuthState.waiting_age)
async def got_age(message: types.Message, state: FSMContext):
    text = (message.text or '').strip()

    if not text.isdigit():
        await message.answer("Yoshingizni faqat raqam bilan yozing. Masalan: <b>21</b>")
        return

    await state.finish()

    ok, response = await site_api.request_code(**user_fields(message.from_user), age=int(text))
    await respond(message.chat.id, ok, response)


@dp.message_handler(state=AuthState.waiting_contact)
async def remind_contact(message: types.Message):
    await message.answer("Pastdagi tugmani bosing 👇", reply_markup=contact_keyboard())


async def respond(chat_id, ok: bool, response: dict):
    """Sayt javobiga qarab: kod beradi yoki keyingi savolni so'raydi."""
    if ok:
        await bot.send_message(
            chat_id,
            f"<b>Kodingiz:</b>\n\n<code>{response['code']}</code>\n\n"
            "Saytga kiriting. Kod 5 daqiqa amal qiladi.\n"
            "Yangi kod kerak bo'lsa — /start bosing.",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        return

    error = response.get('error')

    if error == 'need_phone':
        await AuthState.waiting_contact.set()
        await bot.send_message(
            chat_id,
            "Assalomu alaykum! Saytga kirish uchun raqamingizni yuboring 👇",
            reply_markup=contact_keyboard(),
        )
    elif error == 'need_age':
        await AuthState.waiting_age.set()
        await bot.send_message(
            chat_id,
            "Rahmat! Endi yoshingizni yozing 👇\n\nMasalan: <b>21</b>",
            reply_markup=types.ReplyKeyboardRemove(),
        )
    elif error == 'bad_age':
        await AuthState.waiting_age.set()
        await bot.send_message(chat_id, "Yoshni to'g'ri yozing (7 dan 100 gacha). Masalan: <b>21</b>")
    elif error == 'age_limit':
        limit = response.get('limit', 30)
        await AuthState.waiting_age.set()
        await bot.send_message(
            chat_id,
            f"😔 Kechirasiz, bu saytga faqat <b>{limit} yoshgacha</b> bo'lgan yoshlar kira oladi.\n\n"
            "Yoshingizni noto'g'ri yozgan bo'lsangiz, qaytadan yozing 👇",
            reply_markup=types.ReplyKeyboardRemove(),
        )
    else:
        await bot.send_message(
            chat_id,
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
