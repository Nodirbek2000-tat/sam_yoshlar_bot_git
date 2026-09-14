"""Sayt (Django) bilan bog'lanish."""

import aiohttp

from data import config

CODE_PATH = "/api/telegram/kod/"
TIMEOUT = aiohttp.ClientTimeout(total=25)


async def request_code(telegram_id, first_name='', last_name='', username='',
                       phone='', age=None, photo=None):
    """Foydalanuvchi ma'lumotlarini yuborib, kirish kodini oladi.

    Raqam faqat birinchi marta kerak — keyin sayt odamni telegram_id bo'yicha taniydi.

    Qaytaradi: (muvaffaqiyatlimi, javob_dict). Kod berilmasa javobdagi
    `error` bot nima qilishini aytadi: `need_phone`, `need_age`,
    `age_limit`, `bad_age`.
    """
    url = config.SITE_URL.rstrip('/') + CODE_PATH
    headers = {'X-Bot-Secret': config.API_SECRET}

    form = aiohttp.FormData()
    form.add_field('telegram_id', str(telegram_id))
    form.add_field('first_name', first_name)
    form.add_field('last_name', last_name)
    form.add_field('username', username)
    form.add_field('phone', phone)
    if age is not None:
        form.add_field('age', str(age))

    if photo:
        form.add_field('photo', photo, filename=f'{telegram_id}.jpg',
                       content_type='image/jpeg')

    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.post(url, data=form, headers=headers) as response:
                try:
                    payload = await response.json()
                except Exception:
                    payload = {'error': f'http_{response.status}'}
                return response.status == 200 and payload.get('ok', False), payload
    except aiohttp.ClientError as error:
        return False, {'error': 'tarmoq', 'detail': str(error)}
    except Exception as error:            # noqa: BLE001
        return False, {'error': 'nomalum', 'detail': str(error)}
