from aiogram.dispatcher.filters.state import State, StatesGroup


class ChannelState(StatesGroup):
    """Majburiy kanal qo'shish."""

    waiting_channel = State()


class AdState(StatesGroup):
    """Reklama yuborish: mazmun → tugmalar → tasdiq."""

    waiting_content = State()
    waiting_buttons = State()
    confirm = State()
