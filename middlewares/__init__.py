from aiogram import Dispatcher

from loader import dp
from .private_only import PrivateOnlyMiddleware
from .throttling import ThrottlingMiddleware


if __name__ == "middlewares":
    # Avval chat turini tekshiramiz: guruh/kanalga javob umuman ketmasin
    dp.middleware.setup(PrivateOnlyMiddleware())
    dp.middleware.setup(ThrottlingMiddleware())
