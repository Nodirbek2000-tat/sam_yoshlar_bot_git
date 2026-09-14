from aiogram.dispatcher.filters.state import State, StatesGroup


class AuthState(StatesGroup):
    """Saytga kirish jarayoni: raqam (bir marta) → yosh → kod."""

    waiting_contact = State()
    waiting_age = State()
