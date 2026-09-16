"""Admin menyusi va majburiy obuna tugmalari."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_menu() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📊 Statistika", callback_data='admin:stats'),
        InlineKeyboardButton("📢 Majburiy kanallar", callback_data='admin:channels'),
        InlineKeyboardButton("📣 Reklama yuborish", callback_data='admin:ad'),
    )
    return keyboard


def back_menu() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("⬅️ Orqaga", callback_data='admin:menu'))
    return keyboard


def channels_menu(channels) -> InlineKeyboardMarkup:
    """Har bir kanal — o'chirish tugmasi; tepada qo'shish."""
    keyboard = InlineKeyboardMarkup(row_width=1)

    for channel in channels:
        mark = '' if channel['is_active'] else '⏸ '
        keyboard.add(InlineKeyboardButton(
            f"🗑 {mark}{channel['title']} · {channel['joined']} ta",
            callback_data=f"admin:channel_del:{channel['id']}",
        ))

    keyboard.add(InlineKeyboardButton("➕ Kanal qo'shish", callback_data='admin:channel_add'))
    keyboard.add(InlineKeyboardButton("⬅️ Orqaga", callback_data='admin:menu'))
    return keyboard


def ad_confirm() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Yuborish", callback_data='ad:send'),
        InlineKeyboardButton("❌ Bekor qilish", callback_data='admin:menu'),
    )
    return keyboard


def ad_buttons_markup(buttons) -> InlineKeyboardMarkup:
    """Reklamaning o'z tugmalari: [{'label': ..., 'url': ...}]."""
    if not buttons:
        return None
    keyboard = InlineKeyboardMarkup(row_width=1)
    for item in buttons:
        keyboard.add(InlineKeyboardButton(item['label'], url=item['url']))
    return keyboard


def subscribe_menu(channels) -> InlineKeyboardMarkup:
    """Obuna bo'lish havolalari va «Tekshirish» tugmasi."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    for channel in channels:
        if channel.get('link'):
            keyboard.add(InlineKeyboardButton(f"📢 {channel['title']}", url=channel['link']))
    keyboard.add(InlineKeyboardButton("✅ Tekshirish", callback_data='sub:check'))
    return keyboard
