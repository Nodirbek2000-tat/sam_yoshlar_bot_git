import asyncio

from aiogram import executor

from loader import dp
import middlewares, filters, handlers
from utils.feed import watch_site
from utils.notify_admins import on_startup_notify
from utils.set_bot_commands import set_default_commands


async def on_startup(dispatcher):
    # Birlamchi komandalar (/start va /help)
    await set_default_commands(dispatcher)

    # Bot ishga tushgani haqida adminga xabar berish
    await on_startup_notify(dispatcher)

    # Saytdagi yangi yangiliklarni obunachilarga yuborib turadigan fon jarayoni
    asyncio.create_task(watch_site())


if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup)
