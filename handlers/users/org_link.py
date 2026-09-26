"""Tashkilot hisobini Telegram'ga ulash.

Tashkilot saytga birinchi marta login-parol bilan kirganda sayt maxsus
havola beradi: ``t.me/<bot>?start=org_<token>``. Havola bosilishi bilan
bot o'zi ``/start`` oladi, tashkilotni taniydi va **faqat raqam** so'raydi —
yosh ham, tuman ham so'ralmaydi. Raqam kelgach Telegram tashkilotga
ulanadi va saytdagi oyna o'zi ichkariga kiradi.

Bu fayl ``start.py`` dan oldin ulanadi: ``/start org_…`` shu yerda ushlanadi,
oddiy ``/start`` esa odatdagidek kod beradi.
"""

import re

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.builtin import CommandStart

from loader import dp
from states.auth import OrgLinkState
from utils import site_api

ORG_LINK = re.compile(r'^org_([A-Za-z0-9_-]{8,60})$')


def contact_keyboard() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("📱 Raqamni yuborish", request_contact=True))
    return keyboard


@dp.message_handler(CommandStart(deep_link=ORG_LINK), state='*')
async def org_start(message: types.Message, state: FSMContext, deep_link: re.Match):
    await state.finish()
    token = deep_link.group(1)

    ok, response = await site_api.org_link(token, message.from_user)
    if ok or response.get('error') != 'need_phone':
        await reply(message, ok, response)
        return

    await OrgLinkState.waiting_contact.set()
    await state.update_data(token=token)
    await message.answer(
        f"Assalomu alaykum! 👋\n\n"
        f"<b>{escape(response.get('organization'))}</b> hisobini Telegram'ga ulaymiz.\n\n"
        "Pastdagi tugmani bosib raqamingizni yuboring 👇",
        reply_markup=contact_keyboard(),
    )


@dp.message_handler(content_types=types.ContentType.CONTACT, state=OrgLinkState.waiting_contact)
async def org_contact(message: types.Message, state: FSMContext):
    contact = message.contact

    if contact.user_id != message.from_user.id:
        await message.answer("O'zingizning raqamingizni yuboring 👇",
                             reply_markup=contact_keyboard())
        return

    token = (await state.get_data()).get('token', '')
    ok, response = await site_api.org_link(token, message.from_user,
                                           phone=contact.phone_number or '')

    if not ok and response.get('error') == 'need_phone':
        await message.answer("Raqamni tugma orqali yuboring 👇", reply_markup=contact_keyboard())
        return

    await state.finish()
    await reply(message, ok, response)


@dp.message_handler(lambda message: not (message.text or '').startswith('/'),
                    state=OrgLinkState.waiting_contact, content_types=types.ContentType.ANY)
async def org_remind(message: types.Message):
    await message.answer("Pastdagi <b>📱 Raqamni yuborish</b> tugmasini bosing 👇",
                         reply_markup=contact_keyboard())


async def reply(message: types.Message, ok: bool, response: dict):
    name = escape(response.get('organization') or 'Tashkilot')
    remove = types.ReplyKeyboardRemove()

    if ok and response.get('already'):
        await message.answer(
            f"✅ <b>{name}</b> hisobi allaqachon shu Telegram'ga ulangan.\n\n"
            "Saytga qaytishingiz mumkin.",
            reply_markup=remove,
        )
        return

    if ok:
        await message.answer(
            f"🎉 <b>Xush kelibsiz, {name}!</b>\n\n"
            "Telegram hisobingiz tashkilotga ulandi.\n"
            "Endi saytga qaytishingiz mumkin — sahifa o'zi ochiladi.\n\n"
            "Keyingi safar saytga login-parol bilan yoki shu botda /start bosib, "
            "kod orqali kirasiz.",
            reply_markup=remove,
        )
        return

    error = response.get('error')
    texts = {
        'expired': "⏳ Havolaning muddati tugagan.\n\n"
                   "Saytda login va parol bilan qaytadan kiring — yangi havola chiqadi.",
        'bad_link': "⚠️ Bu havola yaroqsiz yoki allaqachon ishlatilgan.\n\n"
                    "Saytda login va parol bilan qaytadan kiring — yangi havola chiqadi.",
        'telegram_taken': "❌ Bu Telegram hisob saytda boshqa foydalanuvchiga ulangan.\n\n"
                          "Tashkilot uchun boshqa Telegram hisobdan foydalaning "
                          "yoki administratorga murojaat qiling.",
        'org_taken': f"❌ <b>{name}</b> boshqa Telegram hisobga ulangan.\n\n"
                     "O'zgartirish kerak bo'lsa — administratorga murojaat qiling.",
    }
    await message.answer(
        texts.get(error) or f"Xatolik: <code>{error or 'nomalum'}</code>\n"
                            "Birozdan keyin qayta urinib ko'ring.",
        reply_markup=remove,
    )


def escape(text) -> str:
    """Tashkilot nomi HTML sifatida o'qilib ketmasin."""
    return (str(text or '')
            .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
