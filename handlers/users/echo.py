from aiogram import types

from loader import dp


@dp.message_handler(state=None)
async def bot_echo(message: types.Message):
    """Har qanday boshqa xabarga — /start ni eslatamiz (u raqam yoki kod beradi)."""
    await message.answer("Saytga kirish kodini olish uchun /start bosing 👇")
