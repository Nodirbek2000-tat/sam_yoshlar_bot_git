"""Adminlar uchun /admin: statistika, majburiy kanallar, reklama.

Admin — saytda admin bo'lgan (yoki `.env` dagi ADMINS ro'yxatidagi) odam.
Admin bo'lmaganga bot javob ham bermaydi: panel borligi bilinmasin.
"""

import asyncio

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import (BotBlocked, ChatNotFound, RetryAfter,
                                      TelegramAPIError, UserDeactivated)

from data import config
from keyboards.inline.admin import (ad_buttons_markup, ad_confirm, admin_menu, back_menu,
                                    channels_menu)
from loader import bot, dp
from states.admin import AdState, ChannelState
from utils import site_api

#: Kanalda bot shu huquqda bo'lsa a'zolikni tekshira oladi
ADMIN_STATUSES = ('administrator', 'creator')

#: Reklama yuborishda sekundiga ~20 ta xabar
SEND_DELAY = 0.05


async def is_admin(user_id) -> bool:
    if str(user_id) in config.ADMINS:
        return True
    return await site_api.is_site_admin(user_id)


async def deny(target) -> bool:
    """Admin bo'lmasa — jim qaytamiz."""
    if isinstance(target, types.CallbackQuery):
        if await is_admin(target.from_user.id):
            return False
        await target.answer()
        return True

    return not await is_admin(target.from_user.id)


# --------------------------------------------------------------------------
# Menyu
# --------------------------------------------------------------------------

@dp.message_handler(commands=['admin'], state='*')
async def open_panel(message: types.Message, state: FSMContext):
    if await deny(message):
        return

    await state.finish()
    await message.answer("🛠 <b>Admin panel</b>\n\nKerakli bo'limni tanlang:",
                         reply_markup=admin_menu())


@dp.callback_query_handler(lambda call: call.data == 'admin:menu', state='*')
async def back_to_menu(call: types.CallbackQuery, state: FSMContext):
    if await deny(call):
        return

    await state.finish()
    await call.message.edit_text("🛠 <b>Admin panel</b>\n\nKerakli bo'limni tanlang:",
                                 reply_markup=admin_menu())
    await call.answer()


# --------------------------------------------------------------------------
# Statistika
# --------------------------------------------------------------------------

@dp.callback_query_handler(lambda call: call.data == 'admin:stats', state='*')
async def show_stats(call: types.CallbackQuery):
    if await deny(call):
        return

    await call.answer("Yuklanmoqda…")
    data = await site_api.get_stats()

    if not data:
        await call.message.edit_text("Saytga ulanib bo'lmadi. Birozdan keyin urinib ko'ring.",
                                     reply_markup=back_menu())
        return

    users, site = data['users'], data['site']
    lines = [
        "📊 <b>Statistika</b>",
        "",
        "<b>Foydalanuvchilar</b>",
        f"• Jami: <b>{users['total']}</b>",
        f"• Bot orqali: {users['bot']}",
        f"• Bugun: {users['today']} · Haftada: {users['week']}",
        f"• Yosh: {users['youth']} · Tadbirkor: {users['entrepreneurs']} · "
        f"Startupper: {users['startuppers']}",
        "",
        "<b>Sayt</b>",
        f"• Tashabbus: {site['initiatives']} · Ovoz: {site['votes']}",
        f"• Muammo: {site['problems']} · Taklif: {site['solutions']}",
        f"• Yangilik: {site['news']} · Tadbir: {site['events']} · E'lon: {site['announcements']}",
        f"• Tengdosh: {site['peers']} · Startap: {site['startups']} · "
        f"Biznes: {site['businesses']}",
    ]

    if data['channels']:
        lines += ["", "<b>Kanallar</b>"]
        for channel in data['channels']:
            mark = '' if channel['is_active'] else ' (o\'chiq)'
            lines.append(f"• {channel['title']}{mark} — <b>{channel['joined']}</b> ta qo'shilgan")

    last = data['broadcasts'].get('last')
    if last:
        lines += ["", f"<b>Oxirgi reklama:</b> {last['sent']}/{last['total']} ta yetkazildi"]

    await call.message.edit_text("\n".join(lines), reply_markup=back_menu())


# --------------------------------------------------------------------------
# Majburiy kanallar
# --------------------------------------------------------------------------

@dp.callback_query_handler(lambda call: call.data == 'admin:channels', state='*')
async def show_channels(call: types.CallbackQuery, state: FSMContext):
    if await deny(call):
        return

    await state.finish()
    channels = await site_api.get_channels(only_active=False)

    text = ("📢 <b>Majburiy kanallar</b>\n\n"
            "Bu kanallarga obuna bo'lmagan odamga bot kod bermaydi.\n"
            "Kanal nomini bossangiz — ro'yxatdan o'chadi.")
    if not channels:
        text += "\n\n<i>Hozircha kanal qo'shilmagan.</i>"

    await call.message.edit_text(text, reply_markup=channels_menu(channels))
    await call.answer()


@dp.callback_query_handler(lambda call: call.data == 'admin:channel_add', state='*')
async def ask_channel(call: types.CallbackQuery):
    if await deny(call):
        return

    await ChannelState.waiting_channel.set()
    await call.message.edit_text(
        "➕ <b>Kanal qo'shish</b>\n\n"
        "1. Avval botni o'sha kanalga <b>admin</b> qilib qo'ying.\n"
        "2. Keyin kanaldan istalgan postni shu yerga <b>forward</b> qiling "
        "yoki <code>@kanal_nomi</code> deb yozing.\n\n"
        "Bekor qilish — /bekor",
        reply_markup=back_menu(),
    )
    await call.answer()


@dp.message_handler(state=ChannelState.waiting_channel,
                    content_types=types.ContentType.ANY)
async def save_channel(message: types.Message, state: FSMContext):
    chat = None

    if message.forward_from_chat:
        chat = message.forward_from_chat
    elif message.text:
        name = message.text.strip().replace('https://t.me/', '@').replace('t.me/', '@')
        if not name.startswith('@'):
            name = '@' + name
        try:
            chat = await bot.get_chat(name)
        except TelegramAPIError:
            await message.answer("Bunday kanal topilmadi. Nomini tekshirib qayta yuboring.")
            return

    if chat is None:
        await message.answer("Kanaldan post forward qiling yoki @nomini yozing.")
        return

    # Bot o'sha kanalda admin bo'lmasa — a'zolikni tekshira olmaydi
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat.id, me.id)
    except TelegramAPIError:
        await message.answer(
            "❌ Bot bu kanalga kira olmadi.\n\n"
            "Botni kanalga <b>admin</b> qilib qo'shing va qaytadan yuboring.")
        return

    if member.status not in ADMIN_STATUSES:
        await message.answer(
            "❌ Bot bu kanalda <b>admin emas</b>.\n\n"
            "Obunani tekshirish uchun bot admin bo'lishi shart. "
            "Admin qilib qo'ying va qaytadan yuboring.")
        return

    invite_link = getattr(chat, 'invite_link', '') or ''
    if not invite_link and not chat.username:
        try:
            invite_link = await bot.export_chat_invite_link(chat.id)
        except TelegramAPIError:
            invite_link = ''

    ok, payload = await site_api.add_channel(
        chat_id=chat.id,
        title=chat.title or chat.full_name or 'Kanal',
        username=chat.username or '',
        invite_link=invite_link,
        added_by=message.from_user.id,
    )

    await state.finish()

    if not ok:
        await message.answer(f"Saqlab bo'lmadi: <code>{payload.get('error', 'nomalum')}</code>")
        return

    channels = await site_api.get_channels(only_active=False)
    await message.answer(
        f"✅ <b>{payload['channel']['title']}</b> majburiy kanallar ro'yxatiga qo'shildi.",
        reply_markup=channels_menu(channels))


@dp.callback_query_handler(lambda call: call.data.startswith('admin:channel_del:'), state='*')
async def delete_channel(call: types.CallbackQuery):
    if await deny(call):
        return

    channel_id = call.data.rsplit(':', 1)[-1]
    ok, payload = await site_api.remove_channel(channel_id)
    await call.answer("O'chirildi" if ok else "O'chirib bo'lmadi")

    channels = await site_api.get_channels(only_active=False)
    text = "📢 <b>Majburiy kanallar</b>"
    if ok:
        text += f"\n\n<i>{payload.get('title', '')} o'chirildi.</i>"
    if not channels:
        text += "\n\n<i>Hozircha kanal qo'shilmagan.</i>"

    await call.message.edit_text(text, reply_markup=channels_menu(channels))


# --------------------------------------------------------------------------
# Reklama
# --------------------------------------------------------------------------

@dp.callback_query_handler(lambda call: call.data == 'admin:ad', state='*')
async def ask_ad(call: types.CallbackQuery):
    if await deny(call):
        return

    await AdState.waiting_content.set()
    await call.message.edit_text(
        "📣 <b>Reklama</b>\n\n"
        "Yubormoqchi bo'lgan narsangizni tashlang: matn, rasm, video yoki fayl. "
        "Rasm bilan matn ham bo'lishi mumkin (izoh qilib yozing).\n\n"
        "Bekor qilish — /bekor",
        reply_markup=back_menu(),
    )
    await call.answer()


@dp.message_handler(state=AdState.waiting_content, content_types=types.ContentType.ANY)
async def got_ad_content(message: types.Message, state: FSMContext):
    data = {'kind': 'text', 'file_id': '', 'text': message.html_text if message.text else ''}

    if message.photo:
        data.update(kind='photo', file_id=message.photo[-1].file_id,
                    text=message.html_text if message.caption else '')
    elif message.video:
        data.update(kind='video', file_id=message.video.file_id,
                    text=message.html_text if message.caption else '')
    elif message.document:
        data.update(kind='document', file_id=message.document.file_id,
                    text=message.html_text if message.caption else '')
    elif not message.text:
        await message.answer("Bu turdagi xabarni yubora olmayman. Matn, rasm, video yoki fayl tashlang.")
        return

    await state.update_data(**data)
    await AdState.waiting_buttons.set()
    await message.answer(
        "Tugma qo'shasizmi?\n\n"
        "Har bir qatorga shunday yozing:\n"
        "<code>Batafsil | https://samarqandyoshlari.uz</code>\n\n"
        "Tugmasiz yuborish — /otkazish")


@dp.message_handler(commands=['otkazish'], state=AdState.waiting_buttons)
async def skip_buttons(message: types.Message, state: FSMContext):
    await state.update_data(buttons=[])
    await show_preview(message.chat.id, state)


@dp.message_handler(state=AdState.waiting_buttons)
async def got_buttons(message: types.Message, state: FSMContext):
    buttons = []
    for line in (message.text or '').splitlines():
        if '|' not in line:
            continue
        label, url = [part.strip() for part in line.split('|', 1)]
        if label and url.startswith('http'):
            buttons.append({'label': label[:64], 'url': url})

    if not buttons:
        await message.answer("Tugma topilmadi. Namuna:\n"
                             "<code>Batafsil | https://samarqandyoshlari.uz</code>\n\n"
                             "Tugmasiz yuborish — /otkazish")
        return

    await state.update_data(buttons=buttons)
    await show_preview(message.chat.id, state)


async def show_preview(chat_id, state: FSMContext):
    data = await state.get_data()
    await AdState.confirm.set()

    await bot.send_message(chat_id, "👁 <b>Ko'rinishi:</b>")
    await deliver(chat_id, data)

    ids = await site_api.get_user_ids()
    await state.update_data(total=len(ids))
    await bot.send_message(chat_id, f"Shu holda <b>{len(ids)}</b> ta odamga ketadi. Yuboraymi?",
                           reply_markup=ad_confirm())


async def deliver(chat_id, data):
    """Reklamani bitta odamga yuboradi."""
    markup = ad_buttons_markup(data.get('buttons'))
    kind = data.get('kind', 'text')
    text = data.get('text') or ''

    if kind == 'photo':
        return await bot.send_photo(chat_id, data['file_id'], caption=text, reply_markup=markup)
    if kind == 'video':
        return await bot.send_video(chat_id, data['file_id'], caption=text, reply_markup=markup)
    if kind == 'document':
        return await bot.send_document(chat_id, data['file_id'], caption=text, reply_markup=markup)
    return await bot.send_message(chat_id, text, reply_markup=markup)


@dp.callback_query_handler(lambda call: call.data == 'ad:send', state=AdState.confirm)
async def send_ad(call: types.CallbackQuery, state: FSMContext):
    if await deny(call):
        return

    data = await state.get_data()
    await state.finish()
    await call.answer()

    ids = await site_api.get_user_ids()
    broadcast_id = await site_api.start_broadcast(
        text=data.get('text', ''), kind=data.get('kind', 'text'),
        file_id=data.get('file_id', ''), buttons=data.get('buttons') or [],
        total=len(ids), created_by=call.from_user.id)

    progress = await call.message.answer(f"📤 Yuborilmoqda… 0/{len(ids)}")
    sent = failed = blocked = 0

    for index, chat_id in enumerate(ids, start=1):
        try:
            await deliver(chat_id, data)
            sent += 1
        except RetryAfter as error:
            await asyncio.sleep(error.timeout)
            try:
                await deliver(chat_id, data)
                sent += 1
            except TelegramAPIError:
                failed += 1
        except (BotBlocked, UserDeactivated, ChatNotFound):
            blocked += 1
        except TelegramAPIError:
            failed += 1

        if index % 25 == 0:
            try:
                await progress.edit_text(f"📤 Yuborilmoqda… {index}/{len(ids)}")
            except TelegramAPIError:
                pass

        await asyncio.sleep(SEND_DELAY)

    await site_api.finish_broadcast(broadcast_id, sent, failed, blocked)

    await progress.edit_text(
        "✅ <b>Reklama yuborildi</b>\n\n"
        f"• Yetkazildi: <b>{sent}</b>\n"
        f"• Botni bloklaganlar: {blocked}\n"
        f"• Yetmadi: {failed}\n"
        f"• Jami: {len(ids)}",
        reply_markup=admin_menu())


# --------------------------------------------------------------------------
# Bekor qilish
# --------------------------------------------------------------------------

@dp.message_handler(commands=['bekor'], state='*')
async def cancel(message: types.Message, state: FSMContext):
    if await state.get_state() is None:
        return
    await state.finish()
    await message.answer("Bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
