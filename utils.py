import asyncio
import html
import re
import time

from aiogram import Bot
from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup

import db
from config import ADMIN_IDS

OK_STATUSES = {"creator", "administrator", "member"}
_join_cache: dict[int, float] = {}
_admin_cache: dict[int, tuple[float, set[int]]] = {}
JOIN_CACHE_TTL = 600
ADMIN_CACHE_TTL = 300

# تلگرام سه رنگ پس‌زمینه برای دکمه دارد: قرمز، سبز، آبی. رنگین‌کمانی پشت سر هم چیده می‌شوند.
RED, GREEN, BLUE = "danger", "success", "primary"
RAINBOW = (RED, GREEN, BLUE)


# ---------------------------------------------------------------- دکمه رنگی
BOT_USERNAME = ""
ADMIN_RIGHTS = "delete_messages+pin_messages+invite_users+restrict_members+manage_chat"


def add_group_url() -> str:
    return f"https://t.me/{BOT_USERNAME}?startgroup=jinx&admin={ADMIN_RIGHTS}"


def add_channel_url() -> str:
    return f"https://t.me/{BOT_USERNAME}?startchannel=jinx&admin=post_messages+invite_users+manage_chat"


def B(text: str, cb: str | None = None, url: str | None = None, style: str | None = None,
      copy: str | None = None) -> dict:
    return {"text": text, "cb": cb, "url": url, "style": style, "copy": copy}


def kb(rows: list[list[dict]], rainbow: bool = True) -> InlineKeyboardMarkup:
    out, i = [], 0
    for row in rows:
        r = []
        for b in row:
            style = b["style"] or (RAINBOW[i % 3] if rainbow else None)
            i += 1
            extra = {"copy_text": CopyTextButton(text=b["copy"][:256])} if b.get("copy") else {}
            r.append(InlineKeyboardButton(text=b["text"], callback_data=b.get("cb"), url=b.get("url"), style=style, **extra))
        out.append(r)
    return InlineKeyboardMarkup(inline_keyboard=out)


def chunk(items: list, n: int) -> list[list]:
    return [items[i:i + n] for i in range(0, len(items), n)]


# ---------------------------------------------------------------- عمومی
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def mention(user) -> str:
    return f'<a href="tg://user?id={user.id}">{html.escape(user.full_name or "کاربر")}</a>'


def user_handle(user) -> str:
    return f"@{user.username}" if user.username else f"<code>{user.id}</code>"


def support() -> str:
    s = (db.get_setting("support") or "@SuperJinx2").strip()
    return s if s.startswith("@") else "@" + s


def brand() -> str:
    return (db.get_setting("brand") or "Super JinX").strip()


def channel_url() -> str:
    c = (db.get_setting("channel") or "").strip()
    if not c:
        return ""
    if c.startswith("@"):
        return f"https://t.me/{c[1:]}"
    if c.startswith("t.me/"):
        return "https://" + c
    return c


def protected_names() -> list[str]:
    names = [support(), BOT_USERNAME]
    c = db.get_setting("channel") or ""
    if "t.me/" in c or c.startswith("@"):
        names.append(c.rstrip("/").split("/")[-1])
    return [n for n in names if n]


def support_url() -> str:
    return f"https://t.me/{support().lstrip('@')}"


def support_kb() -> InlineKeyboardMarkup:
    rows = [[B("💬 پیام به پشتیبانی", url=support_url(), style=GREEN)]]
    if channel_url():
        rows.append([B(f"📢 کانال {brand()}", url=channel_url(), style=BLUE)])
    return kb(rows)


def support_text() -> str:
    s = support()
    return (
        f"💎 <b>پشتیبانی {html.escape(brand())}</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        + ("🤖 من <b>جینکس</b> هستم؛ سؤالت درباره نصب پنل، Railway، GitHub یا کانفیگ را همین‌جا بپرس.\n\n"
           if db.flag("pv_help") else "🤖 پیوی این ربات مخصوص ادمین است.\n\n")
        + "🛒 برای <b>خرید پنل و کانفیگ</b>\n"
        "🛠 برای <b>مشکل در نصب، Railway و GitHub</b>\n"
        "📩 و هر سؤال دیگر\n\n"
        f"👤 به پشتیبانی پیام بدهید: {s}\n\n"
        "⚡️ <i>پاسخ‌گویی سریع و حرفه‌ای</i>"
    )


def buy_text(user) -> str:
    return (
        f"🛍 {mention(user)} عزیز\n\n"
        "برای <b>خرید پنل، کانفیگ و سرویس</b> مستقیم به پشتیبانی پیام بده 👇\n\n"
        f"👤 {support()}\n"
        "⚡️ <i>جواب سریع می‌گیری</i>"
    )


DEFAULT_WELCOME = (
    "🌹 <b>خوش اومدی {name}!</b>\n"
    "━━━━━━━━━━━━━━━\n\n"
    "🆔 آیدی: {id}\n"
    "🏠 گروه: <b>{group}</b>\n\n"
    "🤖 من <b>جینکس</b> هستم، دستیار هوشمند {brand}. هر سؤالی داشتی بپرس!\n"
    "📚 آموزش نصب پنل، Railway، GitHub و کانفیگ: دکمه راهنما\n"
    "🛒 خرید پنل و کانفیگ: {support}\n\n"
    "⚠️ <i>تبلیغات، لینک کانال و گروه، دعوت به پیوی، فحاشی و تهدید ممنوع است.</i>"
)


def welcome_text(user, chat) -> str:
    tpl = db.get_setting("welcome_text") or DEFAULT_WELCOME
    return (
        tpl.replace("{name}", mention(user))
        .replace("{id}", user_handle(user))
        .replace("{group}", html.escape(chat.title or ""))
        .replace("{support}", support())
        .replace("{brand}", html.escape(brand()))
    )


def welcome_kb() -> InlineKeyboardMarkup:
    rows = [[B("📚 راهنماها", cb="g:menu", style=BLUE), B("💬 پشتیبانی", url=support_url(), style=GREEN)]]
    if channel_url():
        rows.append([B(f"📢 کانال {brand()}", url=channel_url(), style=RED)])
    return kb(rows)


# ---------------------------------------------------------------- جوین اجباری
def fj_enabled() -> bool:
    return db.flag("fj_enabled")


def clear_join_cache(user_id: int):
    _join_cache.pop(user_id, None)


async def missing_channels(bot: Bot, user_id: int) -> list[dict]:
    if not fj_enabled() or is_admin(user_id):
        return []
    channels = db.list_channels()
    if not channels:
        return []
    t = _join_cache.get(user_id)
    if t and time.time() - t < JOIN_CACHE_TTL:
        return []

    async def check(ch):
        try:
            m = await bot.get_chat_member(ch["chat_id"], user_id)
            status = getattr(m.status, "value", m.status)
            return status in OK_STATUSES or (status == "restricted" and getattr(m, "is_member", False))
        except Exception:
            return True  # اگر ربات نتوانست چک کند، کاربر را بلاک نکن

    results = await asyncio.gather(*(check(ch) for ch in channels))
    missing = [ch for ch, ok in zip(channels, results) if not ok]
    if not missing:
        _join_cache[user_id] = time.time()
    return missing


def join_kb(channels: list[dict], owner_id: int = 0) -> InlineKeyboardMarkup:
    rows = [[B(f"📢 عضویت در {ch['title']}", url=ch["link"])] for ch in channels]
    rows.append([B("✅ عضو شدم", cb=f"fj:chk:{owner_id}", style=GREEN)])
    return kb(rows)


def join_text(user=None) -> str:
    who = f"{mention(user)} عزیز\n\n" if user else ""
    return (
        f"🔐 {who}"
        "برای استفاده از گروه، اول عضو کانال‌های ما شو 👇\n\n"
        "✨ <i>بعد از عضویت، دکمه «عضو شدم» را بزن.</i>"
    )


async def is_group_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    cached = _admin_cache.get(chat_id)
    if not cached or time.time() - cached[0] > ADMIN_CACHE_TTL:
        try:
            admins = await bot.get_chat_administrators(chat_id)
            ids = {a.user.id for a in admins}
        except Exception:
            ids = set()
        _admin_cache[chat_id] = (time.time(), ids)
        cached = _admin_cache[chat_id]
    return user_id in cached[1]


async def delete_later(message, seconds: int):
    await asyncio.sleep(seconds)
    try:
        await message.delete()
    except Exception:
        pass


# ---------------------------------------------------------------- راهنماها
def guides_menu_kb() -> InlineKeyboardMarkup:
    btns = [B(g["title"], cb=f"g:{g['id']}") for g in db.list_guides()]
    rows = chunk(btns, 2)
    last = [B("💬 پشتیبانی", url=support_url(), style=GREEN)]
    if channel_url():
        last.append(B("📢 کانال ما", url=channel_url(), style=BLUE))
    rows.append(last)
    return kb(rows)


def back_to_menu_kb(extra: list[dict] | None = None) -> InlineKeyboardMarkup:
    rows = [[b] for b in (extra or [])]
    rows.append([B("📚 همه راهنماها", cb="g:menu", style=BLUE), B("💬 پشتیبانی", url=support_url(), style=GREEN)])
    return kb(rows)


def links_menu_kb(links: list[dict]) -> InlineKeyboardMarkup:
    rows = [[B(l["title"], url=l["url"])] for l in links]
    rows.append([B("💬 پشتیبانی", url=support_url(), style=GREEN)])
    return kb(rows)


def match_links(text: str) -> list[dict]:
    t = normalize(text)
    out = []
    for l in db.list_links():
        kws = [normalize(k) for k in re.split(r"[,،]", l["keywords"] or "") if k.strip()]
        if any(k and k in t for k in kws):
            out.append(l)
    return out


LINK_ASK = ("لینک", "link", "ادرس", "آدرس", "ریپو", "repo", "سورس", "source", "دانلود", "download", "بفرست", "بدید", "بده")


_AR_FIX = str.maketrans({"ي": "ی", "ك": "ک", "\u200c": " ", "ة": "ه", "آ": "ا"})
QUESTION_HINTS = (
    "?", "؟", "چطور", "چجوری", "چجور", "چطوری", "چگونه", "کمک", "راهنما", "اموزش",
    "نصب", "مشکل", "نمیشه", "نمی شه", "نمیکنه", "نمی کنه", "خطا", "ارور", "error", "کسی", "بلده", "میشه",
    "نشد", "نمیتونم", "نمی تونم", "بالا نمیاد", "نمیاد", "crash", "fail", "کرش", "دیپلوی", "deploy",
    "باگ", "گیر کردم", "گیر کرده", "کار نمیده", "چیکار کنم", "چکار کنم", "failed", "not found", "exception",
    "traceback", "denied", "refused", "502", "404", "500", "لاگ", "log", "درست نمیشه", "چرا", "کجا", "کدوم",
)
TOPIC_WORDS = (
    "پنل", "کانفیگ", "config", "railway", "ریلوی", "رلوی", "github", "گیتهاب", "گیت هاب", "گیتاب", "سرور", "اینباند",
    "inbound", "ساب", "sub", "vless", "vmess", "trojan", "reality", "ریالیتی", "xray", "ایکس ری", "مرزبان", "marzban",
    "ثنایی", "پاسارگارد", "pasarguard", "جینکس", "jinx", "دیپلوی", "deploy", "دامنه", "domain", "ssl", "پورت", "port",
    "v2ray", "نود", "node", "هیدیفای", "hiddify", "کلاینت", "volume", "ولوم", "docker", "داکر", "ریپو", "repo",
    "فیلترشکن", "vpn", "وی پی ان", "اتصال", "وصل", "ping", "پینگ", "اپلود", "upload", "build", "بیلد", "لاگ",
)


def on_topic(text: str) -> bool:
    t = normalize(text)
    return any(w in t for w in TOPIC_WORDS)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").translate(_AR_FIX).lower()).strip()


def looks_like_question(text: str) -> bool:
    t = normalize(text)
    return any(h in t for h in QUESTION_HINTS)


def match_guide(text: str) -> dict | None:
    t = normalize(text)
    if not t:
        return None
    best, best_score = None, 0
    for g in db.list_guides():
        kws = [normalize(k) for k in re.split(r"[,،]", g["keywords"] or "") if k.strip()]
        score = sum(len(k) * (2 if " " in k else 1) for k in set(kws) if k and k in t)
        if score > best_score:
            best, best_score = g, score
    return best


# ---------------------------------------------------------------- دکمه‌های پست
def parse_spec(raw: str) -> list[list[dict]]:
    """هر خط یک ردیف؛ دکمه‌های یک ردیف با && جدا می‌شوند؛ هر دکمه: متن | لینک"""
    rows = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        row = []
        for part in line.split("&&"):
            if "|" not in part:
                raise ValueError(part.strip())
            text, url = (x.strip() for x in part.split("|", 1))
            if not text or not re.match(r"^(https?://|tg://)", url):
                raise ValueError(part.strip())
            row.append(B(text, url=url))
        rows.append(row)
    return rows


def parse_buttons(raw: str) -> InlineKeyboardMarkup | None:
    rows = parse_spec(raw)
    return kb(rows) if rows else None
