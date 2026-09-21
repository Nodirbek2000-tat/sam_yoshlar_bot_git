from aiogram.dispatcher.filters.state import State, StatesGroup


class AuthState(StatesGroup):
    """Saytga kirish jarayoni: raqam (bir marta) → yosh → tuman → kod."""

    waiting_contact = State()
    waiting_age = State()
    waiting_district = State()
