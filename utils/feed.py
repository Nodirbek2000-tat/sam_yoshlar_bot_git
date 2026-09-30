"""Saytdagi yangiliklarni obunachilarga yuborish.

Saytga yangi yangilik, e'lon, startap, tadbirkor yoki tengdosh qo'shilsa,
u navbatga tushadi. Bot har daqiqada navbatni tekshiradi va hammaga
rasm, matn boshlanishi va «Davomini o'qish» tugmasi bilan yuboradi.

Panelda «Botga yuborish» o'chirilgan bo'lsa — navbatga hech narsa
tushmaydi, demak hech kimga hech narsa bormaydi.
"""

import asyncio
import logging

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from data import config
from aiogram.utils.exceptions import (BotBlocked, ChatNotFound, RetryAfter,
                                      TelegramAPIError, UserDeactivated)

from loader import bot
from utils import site_api

#: Navbat shu oraliqda tekshiriladi (soniya)
CHECK_EVERY = 60

#: Shaxsiy xabarlar tezroq tekshiriladi — odam darhol bilsin
DIRECT_EVERY = 5

#: Sekundiga ~20 ta xabar
SEND_DELAY = 0.05

#: Har bir turga o'z belgisi
EMOJI = {
    'news': '📰',
    'announcement': '📣',
    'startup': '🚀',
    'business': '💼',
    'peer': '🌍',
}

logger = logging.getLogger(__name__)


def caption(post):
    mark = EMOJI.get(post['kind'], '✨')
    lines = [f"{mark} <b>{post['title']}</b>"]
    if post.get('excerpt'):
        lines += ['', post['excerpt']]
    return "\n".join(lines)


def keyboard(post):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📖 Davomini o'qish", url=post['link']))
    return markup


async def deliver(chat_id, post):
    """Bitta odamga yuboradi: rasm bo'lsa rasm bilan."""
    markup = keyboard(post)
    text = caption(post)

    if post.get('image'):
        try:
            return await bot.send_photo(chat_id, post['image'], caption=text, reply_markup=markup)
        except (BotBlocked, UserDeactivated, ChatNotFound, RetryAfter):
            raise
        except TelegramAPIError:
            # Rasm ochilmasa — matn bilan yuboramiz
            pass

    return await bot.send_message(chat_id, text, reply_markup=markup,
                                  disable_web_page_preview=False)


async def send_post(post, user_ids):
    sent = failed = 0

    for chat_id in user_ids:
        try:
            await deliver(chat_id, post)
            sent += 1
        except RetryAfter as error:
            await asyncio.sleep(error.timeout)
            try:
                await deliver(chat_id, post)
                sent += 1
            except TelegramAPIError:
                failed += 1
        except (BotBlocked, UserDeactivated, ChatNotFound):
            failed += 1
        except TelegramAPIError:
            failed += 1

        await asyncio.sleep(SEND_DELAY)

    await site_api.post_result(post['id'], len(user_ids), sent, failed)
    logger.info("Yangilik yuborildi: %s -> %s/%s", post['title'], sent, len(user_ids))


def escape(text):
    return str(text or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


async def report_errors():
    """Serverda xato chiqsa — `.env` dagi ADMINS ga darhol xabar."""
    errors, panel = await site_api.get_errors()

    for error in errors:
        head = "🔁 Xato yana takrorlandi" if error.get('repeat') else "⚠️ Serverda yangi xato"
        lines = [
            f"<b>{head}</b>",
            "",
            f"<code>{escape(error['title'])[:300]}</code>",
            f"📍 {escape(error.get('location') or '—')}",
            f"🌐 {escape(error.get('method'))} {escape(error.get('path'))[:200]}",
            f"🔢 Jami: {error.get('count', 1)} marta",
        ]
        markup = None
        if panel.startswith('https://'):
            markup = InlineKeyboardMarkup().add(
                InlineKeyboardButton("🛠 Panelda ko'rish", url=panel))

        for admin in config.ADMINS:
            try:
                await bot.send_message(admin, "\n".join(lines), reply_markup=markup)
            except TelegramAPIError as problem:
                logger.warning("Adminga xato haqida yozib bo'lmadi (%s): %s", admin, problem)


async def send_direct():
    """Shaxsiy xabarlar: sayt navbatga qo'yadi, bot egasiga yetkazadi."""
    messages = await site_api.get_messages()
    if not messages:
        return

    results = []
    for message in messages:
        markup = None
        if message.get('buttons'):
            markup = InlineKeyboardMarkup(row_width=1)
            for button in message['buttons']:
                markup.add(InlineKeyboardButton(button['text'], url=button['url']))

        async def deliver_once():
            await bot.send_message(message['telegram_id'], message['text'],
                                   reply_markup=markup, disable_web_page_preview=True)

        try:
            try:
                await deliver_once()
            except RetryAfter as error:
                await asyncio.sleep(error.timeout)
                await deliver_once()
            results.append({'id': message['id'], 'ok': True})
        except TelegramAPIError as problem:
            # Botni bloklagan yoki hisobini o'chirgan — saytdagi bildirishnoma baribir qoladi
            results.append({'id': message['id'], 'ok': False, 'error': str(problem)[:200]})

        await asyncio.sleep(SEND_DELAY)

    await site_api.messages_result(results)


async def watch_direct():
    """Shaxsiy xabarlar sikli — `watch_site` dan alohida, tezroq yuradi."""
    while True:
        try:
            await send_direct()
        except Exception as error:            # noqa: BLE001
            logger.warning("Shaxsiy xabarlarni yuborishda xato: %s", error)

        await asyncio.sleep(DIRECT_EVERY)


async def watch_site():
    """Doimiy sikl — bot ishlab turganda fonda yuradi."""
    while True:
        try:
            posts = await site_api.get_posts()
            if posts:
                user_ids = await site_api.get_user_ids()
                for post in posts:
                    await send_post(post, user_ids)
        except Exception as error:            # noqa: BLE001
            logger.warning("Yangiliklarni yuborishda xato: %s", error)

        try:
            await report_errors()
        except Exception as error:            # noqa: BLE001
            logger.warning("Server xatolarini yuborishda xato: %s", error)

        await asyncio.sleep(CHECK_EVERY)
