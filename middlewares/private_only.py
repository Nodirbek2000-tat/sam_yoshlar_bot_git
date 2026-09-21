"""Bot faqat shaxsiy yozishmada ishlaydi.

Bot majburiy obuna kanaliga yoki biror guruhga admin qilib qo'shilsa,
o'sha yerdagi xabarlarga javob bermasligi kerak: kod ham, eslatma ham
faqat odamning o'ziga, shaxsiy chatga boradi.
"""

from aiogram import types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware


def _is_private(chat) -> bool:
    return chat is not None and chat.type == types.ChatType.PRIVATE


class PrivateOnlyMiddleware(BaseMiddleware):
    """Shaxsiy chatdan tashqaridagi hamma yangilanishni jimgina to'xtatadi."""

    async def on_pre_process_message(self, message: types.Message, data: dict):
        if not _is_private(message.chat):
            raise CancelHandler()

    async def on_pre_process_edited_message(self, message: types.Message, data: dict):
        if not _is_private(message.chat):
            raise CancelHandler()

    async def on_pre_process_channel_post(self, message: types.Message, data: dict):
        raise CancelHandler()

    async def on_pre_process_edited_channel_post(self, message: types.Message, data: dict):
        raise CancelHandler()

    async def on_pre_process_callback_query(self, call: types.CallbackQuery, data: dict):
        if call.message is not None and not _is_private(call.message.chat):
            raise CancelHandler()
