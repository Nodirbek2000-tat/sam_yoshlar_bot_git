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
from aiogram.utils.exceptions import (BotBlocked, ChatNotFound, RetryAfter,
                                      TelegramAPIError, UserDeactivated)

from loader import bot
from utils import site_api

#: Navbat shu oraliqda tekshiriladi (soniya)
CHECK_EVERY = 60

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

        await asyncio.sleep(CHECK_EVERY)
