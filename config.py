"""تنظیمات از متغیرهای محیطی (Railway Variables یا فایل .env)."""
import os
import re

from dotenv import load_dotenv

load_dotenv()

_FA = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _env(name: str, default: str = "") -> str:
    v = os.getenv(name, default) or ""
    return v.strip().strip('"').strip("'").strip()


BOT_TOKEN = _env("BOT_TOKEN")
# آیدی عددی ادمین‌ها؛ چندتا را با کاما یا فاصله جدا کنید
ADMIN_IDS = {int(x) for x in re.findall(r"-?\d{4,}", _env("ADMIN_IDS").translate(_FA))}
# اختیاری: پروکسی برای سرورهایی که به تلگرام دسترسی ندارند (مثل socks5://127.0.0.1:1080)
PROXY = _env("PROXY") or None
DB_PATH = _env("DB_PATH", "data/bot.db") or "data/bot.db"

# پروکسی جدا برای API هوش مصنوعی (اختیاری)
AI_PROXY = _env("AI_PROXY") or PROXY
# هوش مصنوعی ابری (اختیاری؛ از پنل مدیریت هم قابل تنظیم است)
AI_BASE = _env("AI_BASE")
AI_KEY = _env("AI_KEY")
AI_MODEL = _env("AI_MODEL")

# مشخصات برند
BRAND = _env("BRAND", "Super JinX") or "Super JinX"
SUPPORT = _env("SUPPORT", "@SuperJinx2") or "@SuperJinx2"
CHANNEL = _env("CHANNEL")
