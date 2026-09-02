from environs import Env

# environs kutubxonasidan foydalanish
env = Env()
env.read_env()

# .env fayl ichidan quyidagilarni o'qiymiz
BOT_TOKEN = env.str("BOT_TOKEN")            # Bot token
ADMINS = env.list("ADMINS")                 # adminlar ro'yxati
IP = env.str("ip", "localhost")             # Xosting ip manzili

# --- Sayt bilan bog'lanish ---
SITE_URL = env.str("SITE_URL", "http://127.0.0.1:8000")   # Django manzili
API_SECRET = env.str("API_SECRET", "")                     # Django .env dagi TELEGRAM_API_SECRET
