"""Sayt (Django) bilan bog'lanish.

Bot va sayt bitta bazadan ishlaydi: kirish kodi, majburiy kanallar,
statistika va reklama — hammasi shu API orqali.
"""

import aiohttp

from data import config

TIMEOUT = aiohttp.ClientTimeout(total=25)

CODE_PATH = "/api/telegram/kod/"
ADMIN_PATH = "/api/telegram/admin/"
STATS_PATH = "/api/telegram/statistika/"
CHANNELS_PATH = "/api/telegram/kanallar/"
JOINS_PATH = "/api/telegram/obuna/"
USERS_PATH = "/api/telegram/foydalanuvchilar/"
BROADCAST_PATH = "/api/telegram/reklama/"


def _url(path):
    return config.SITE_URL.rstrip('/') + path


def _headers():
    return {'X-Bot-Secret': config.API_SECRET}


async def _request(method, path, *, params=None, json=None):
    """(muvaffaqiyatlimi, javob) — tarmoq uzilsa ham bot yiqilmaydi."""
    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.request(method, _url(path), params=params, json=json,
                                       headers=_headers()) as response:
                try:
                    payload = await response.json()
                except Exception:
                    payload = {'error': f'http_{response.status}'}
                return response.status == 200 and payload.get('ok', False), payload
    except aiohttp.ClientError as error:
        return False, {'error': 'tarmoq', 'detail': str(error)}
    except Exception as error:            # noqa: BLE001
        return False, {'error': 'nomalum', 'detail': str(error)}


# --------------------------------------------------------------------------
# Kirish kodi
# --------------------------------------------------------------------------

async def request_code(telegram_id, first_name='', last_name='', username='',
                       phone='', age=None, photo=None):
    """Foydalanuvchi ma'lumotlarini yuborib, kirish kodini oladi.

    Raqam faqat birinchi marta kerak — keyin sayt odamni telegram_id bo'yicha taniydi.

    Qaytaradi: (muvaffaqiyatlimi, javob_dict). Kod berilmasa javobdagi
    `error` bot nima qilishini aytadi: `need_phone`, `need_age`,
    `age_limit`, `bad_age`.
    """
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
            async with session.post(_url(CODE_PATH), data=form, headers=_headers()) as response:
                try:
                    payload = await response.json()
                except Exception:
                    payload = {'error': f'http_{response.status}'}
                return response.status == 200 and payload.get('ok', False), payload
    except aiohttp.ClientError as error:
        return False, {'error': 'tarmoq', 'detail': str(error)}
    except Exception as error:            # noqa: BLE001
        return False, {'error': 'nomalum', 'detail': str(error)}


# --------------------------------------------------------------------------
# Admin menyusi
# --------------------------------------------------------------------------

async def is_site_admin(telegram_id):
    """Saytda admin bo'lganlar botda ham admin."""
    ok, payload = await _request('GET', ADMIN_PATH, params={'telegram_id': telegram_id})
    return bool(ok and payload.get('is_admin'))


async def get_stats():
    ok, payload = await _request('GET', STATS_PATH)
    return payload if ok else None


# --------------------------------------------------------------------------
# Majburiy kanallar
# --------------------------------------------------------------------------

async def get_channels(only_active=True):
    params = {'faqat_faol': '1'} if only_active else None
    ok, payload = await _request('GET', CHANNELS_PATH, params=params)
    return payload.get('results', []) if ok else []


async def add_channel(chat_id, title, username='', invite_link='', added_by=None):
    return await _request('POST', CHANNELS_PATH, json={
        'chat_id': chat_id, 'title': title, 'username': username,
        'invite_link': invite_link, 'added_by': added_by,
    })


async def remove_channel(channel_id):
    return await _request('DELETE', f"{CHANNELS_PATH}{channel_id}/")


async def record_joins(telegram_id, chat_ids):
    """Obuna tekshiruvidan o'tganda — kim qaysi kanalga qo'shilgani yoziladi."""
    return await _request('POST', JOINS_PATH,
                          json={'telegram_id': telegram_id, 'chat_ids': list(chat_ids)})


# --------------------------------------------------------------------------
# Reklama
# --------------------------------------------------------------------------

async def get_user_ids():
    ok, payload = await _request('GET', USERS_PATH)
    return payload.get('ids', []) if ok else []


async def start_broadcast(text='', kind='text', file_id='', buttons=None, total=0,
                          created_by=None):
    ok, payload = await _request('POST', BROADCAST_PATH, json={
        'text': text, 'kind': kind, 'file_id': file_id,
        'buttons': buttons or [], 'total': total, 'created_by': created_by,
    })
    return payload.get('id') if ok else None


async def finish_broadcast(broadcast_id, sent, failed, blocked):
    if not broadcast_id:
        return False, {}
    return await _request('POST', f"{BROADCAST_PATH}{broadcast_id}/natija/",
                          json={'sent': sent, 'failed': failed, 'blocked': blocked})
