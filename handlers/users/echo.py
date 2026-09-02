from aiogram import types

from handlers.users.start import contact_keyboard
from loader import dp


@dp.message_handler(state=None)
async def bot_echo(message: types.Message):
    """Har qanday boshqa xabarga — raqam so'raymiz."""
    await message.answer("Raqamingizni yuboring 👇", reply_markup=contact_keyboard())
