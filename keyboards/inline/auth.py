"""Ro'yxatdan o'tish tugmalari: tuman tanlash."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

#: Sayt javob bermasa ham bot ishlayversin — zaxira ro'yxat
DEFAULT_DISTRICTS = [
    {'value': 'samarqand_shahri', 'label': "Samarqand shahri"},
    {'value': 'kattaqorgon_shahri', 'label': "Kattaqo'rg'on shahri"},
    {'value': 'bulungur', 'label': "Bulung'ur tumani"},
    {'value': 'jomboy', 'label': "Jomboy tumani"},
    {'value': 'ishtixon', 'label': "Ishtixon tumani"},
    {'value': 'kattaqorgon', 'label': "Kattaqo'rg'on tumani"},
    {'value': 'qoshrabot', 'label': "Qo'shrabot tumani"},
    {'value': 'narpay', 'label': "Narpay tumani"},
    {'value': 'nurobod', 'label': "Nurobod tumani"},
    {'value': 'oqdaryo', 'label': "Oqdaryo tumani"},
    {'value': 'pastdargom', 'label': "Pastdarg'om tumani"},
    {'value': 'paxtachi', 'label': "Paxtachi tumani"},
    {'value': 'payariq', 'label': "Payariq tumani"},
    {'value': 'samarqand_tumani', 'label': "Samarqand tumani"},
    {'value': 'toyloq', 'label': "Toyloq tumani"},
    {'value': 'urgut', 'label': "Urgut tumani"},
]


def districts_menu(districts=None) -> InlineKeyboardMarkup:
    """Tumanlar ro'yxati — ikki ustun qilib chiqadi."""
    keyboard = InlineKeyboardMarkup(row_width=2)
    row = []

    for item in districts or DEFAULT_DISTRICTS:
        row.append(InlineKeyboardButton(item['label'],
                                        callback_data=f"tuman:{item['value']}"))
        if len(row) == 2:
            keyboard.row(*row)
            row = []

    if row:
        keyboard.row(*row)
    return keyboard
