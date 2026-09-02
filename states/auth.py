from aiogram.dispatcher.filters.state import State, StatesGroup


class AuthState(StatesGroup):
    """Saytga kirish jarayoni."""

    waiting_contact = State()
