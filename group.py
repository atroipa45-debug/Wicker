"""گروه: خوش‌آمدگویی، هوش مصنوعی، ارسال لینک، ارجاع خرید."""
import asyncio
import html
import logging
import time

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import ChatMemberUpdated, Message

import ai, brain, db
from config import ADMIN_IDS
from filters import wants_to_buy
from utils import (
    LINK_ASK, B, back_to_menu_kb, buy_text, guides_menu_kb, links_menu_kb, looks_like_question, match_links,
    normalize, on_topic, support_kb, welcome_kb, welcome_text,
)
from common import menu_text

log = logging.getLogger("group")
router = Router(name="group")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

_cooldown: dict[tuple, float] = {}
_last_welcome: dict[int, int] = {}
COOLDOWN = 60
AI_USER_COOLDOWN = 4
CALL_NAMES = ("جینکس", "jinx", "ربات ", "ربات،", "ربات جان")


def _cool(key, seconds) -> bool:
    """True یعنی هنوز در زمان انتظار است."""
    now = time.time()
    if now - _cooldown.get(key, 0) < seconds:
        return True
    _cooldown[key] = now
    return False


async def _owner_inside(bot: Bot, chat_id: int) -> bool:
    """اگر یکی از ادمین‌های ربات، مدیر آن گروه باشد، گروه مال خودمان است."""
    for aid in ADMIN_IDS:
        try:
            m = await bot.get_chat_member(chat_id, aid)
            if getattr(m.status, "value", m.status) in ("creator", "administrator"):
                return True
        except Exception:
            pass
    return False


@router.message(F.migrate_from_chat_id)
async def migrated(msg: Message):
    db.del_group(msg.migrate_from_chat_id)
    db.upsert_group(msg.chat.id, msg.chat.title or str(msg.chat.id))


@router.my_chat_member()
async def bot_membership(ev: ChatMemberUpdated, bot: Bot):
    if ev.chat.type not in ("group", "supergroup"):
        return
    status = getattr(ev.new_chat_member.status, "value", ev.new_chat_member.status)
    old = getattr(ev.old_chat_member.status, "value", ev.old_chat_member.status)
    if status in ("member", "administrator"):
        # 🔒 قفل ضد کپی: فقط ادمین‌های ربات می‌توانند ربات را به گروه اضافه کنند
        adder = ev.from_user.id if ev.from_user else 0
        if old in ("left", "kicked") and db.flag("lock") and adder not in ADMIN_IDS and not await _owner_inside(bot, ev.chat.id):
            try:
                await bot.send_message(ev.chat.id, "⛔️ <b>این ربات اختصاصی است</b> و فقط مالک آن می‌تواند ربات را به گروه اضافه کند.")
            except Exception:
                pass
            try:
                await bot.leave_chat(ev.chat.id)
            except Exception:
                pass
            for aid in ADMIN_IDS:
                try:
                    await bot.send_message(aid, f"🚨 یک نفر (<code>{adder}</code>) ربات را به گروه "
                                                f"<b>{html.escape(ev.chat.title or '')}</b> اضافه کرد؛ ربات خودکار خارج شد.")
                except Exception:
                    pass
            return
        db.upsert_group(ev.chat.id, ev.chat.title or str(ev.chat.id))
        if old in ("left", "kicked") or status != old:
            note = ("✅ ربات <b>ادمین</b> است و همه‌چیز آماده است." if status == "administrator"
                    else "⚠️ ربات هنوز <b>ادمین نیست</b>؛ برای حذف لینک و فحش، ادمینش کنید.")
            for aid in ADMIN_IDS:
                try:
                    await bot.send_message(aid, f"👥 ربات به گروه <b>{html.escape(ev.chat.title or '')}</b> وصل شد.\n{note}")
                except Exception:
                    pass
    elif status in ("left", "kicked"):
        db.del_group(ev.chat.id)


@router.chat_member()
async def on_join(ev: ChatMemberUpdated, bot: Bot):
    if ev.chat.type not in ("group", "supergroup"):
        return
    old = getattr(ev.old_chat_member.status, "value", ev.old_chat_member.status)
    new = getattr(ev.new_chat_member.status, "value", ev.new_chat_member.status)
    was_in = old in ("member", "administrator", "creator") or (old == "restricted" and ev.old_chat_member.is_member)
    now_in = new in ("member", "administrator", "creator") or (new == "restricted" and ev.new_chat_member.is_member)
    user = ev.new_chat_member.user
    if was_in or not now_in or user.is_bot:
        return
    # 🎭 جعل هویت: همان لحظه ورود بن می‌شود
    if db.flag("anti_fake") and user.id not in ADMIN_IDS:
        from middlewares import fake_user
        if fake_user(user):
            try:
                await bot.ban_chat_member(ev.chat.id, user.id)
                db.bump("del_fake")
            except Exception:
                pass
            return
    db.remember_user(user.username, user.id)
    if not db.flag("welcome_on"):
        return
    prev = _last_welcome.pop(ev.chat.id, None)
    if prev:
        try:
            await bot.delete_message(ev.chat.id, prev)
        except Exception:
            pass
    try:
        m = await bot.send_message(ev.chat.id, welcome_text(user, ev.chat), reply_markup=welcome_kb())
        _last_welcome[ev.chat.id] = m.message_id
    except Exception:
        pass


@router.message(F.new_chat_members | F.left_chat_member)
async def service_msg(msg: Message):
    if not db.flag("del_service"):
        return
    try:
        await msg.delete()  # پیام سیستمی «فلانی وارد شد» پاک می‌شود؛ خوش‌آمد خود ربات کافی است
    except Exception:
        pass


@router.edited_message()
async def edited(_: Message):
    pass


@router.message(Command("guide", "help", "start"))
@router.message(F.text.in_({"راهنما", "منو", "آموزش", "اموزش"}))
async def group_menu(msg: Message):
    await msg.reply(menu_text(), reply_markup=guides_menu_kb())


@router.message(Command("reset"))
async def reset_mem(msg: Message):
    if msg.from_user is None:
        return
    ai.forget(msg.chat.id, msg.from_user.id)
    await msg.reply("🧠 حافظه گفتگوی ما پاک شد. از اول بپرس!")


async def _keep_typing(bot: Bot, chat_id: int, stop: asyncio.Event):
    while not stop.is_set():
        try:
            await bot.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop.wait(), 4.5)
        except asyncio.TimeoutError:
            pass


async def ai_reply(msg: Message, bot: Bot, text: str, image: bytes | None, context: str | None) -> bool:
    stop = asyncio.Event()
    typing = asyncio.create_task(_keep_typing(bot, msg.chat.id, stop))
    try:
        out = await ai.answer(msg.chat.id, msg.from_user.id, msg.from_user.first_name or "کاربر", text,
                              msg.chat.title or "", image=image, context=context)
    except Exception as e:
        log.warning("AI failed: %s", e)
        return False
    finally:
        stop.set()
        typing.cancel()
    if not out:
        return False
    body, tags = ai.render(out)
    extra = []
    for kind, i in tags:
        if kind == "link" and (l := db.get_link(i)):
            extra.append(B(l["title"], url=l["url"]))
        elif kind == "guide" and (g := db.get_guide(i)):
            extra.append(B(f"📖 {g['title']}", cb=f"g:{g['id']}"))
    markup = back_to_menu_kb(extra)
    try:
        await msg.reply(body, reply_markup=markup)
    except Exception:
        await msg.reply(ai.TAG_RE.sub("", out)[:4000], reply_markup=markup, parse_mode=None)
    return True


@router.message(F.text | F.caption | F.photo)
async def group_text(msg: Message, bot: Bot):
    if msg.from_user is None or msg.from_user.is_bot:
        return
    me = await bot.me()
    text = msg.text or msg.caption or ""
    low = normalize(text)
    reply_to_bot = (msg.reply_to_message is not None and msg.reply_to_message.from_user is not None
                    and msg.reply_to_message.from_user.id == me.id)
    addressed = (bool(me.username and f"@{me.username.lower()}" in low) or reply_to_bot
                 or low == "ربات" or any(low.startswith(n) for n in CALL_NAMES))

    # 🛒 خرید
    if db.flag("buy_reply") and wants_to_buy(text):
        if not _cool(("buy", msg.from_user.id), COOLDOWN):
            await msg.reply(buy_text(msg.from_user), reply_markup=support_kb())
        return

    # 🔗 لینک‌های مهم (گیتهاب و ...) بدون معطلی
    if any(w in low for w in LINK_ASK):
        links = match_links(text)
        if links:
            if not _cool(("link", msg.chat.id, tuple(l["id"] for l in links)), 20) or addressed:
                await msg.reply("🔗 <b>بفرما، لینک‌های رسمی</b> 👇", reply_markup=links_menu_kb(links))
            return

    # 🧠 تصمیم برای جواب دادن
    diag = brain.diagnose(text) if text else None
    if not addressed:
        if not db.flag("auto_answer") or not text:
            return
        if not diag:
            if not on_topic(text):
                return
            if not db.flag("ai_all") and not (looks_like_question(text) or msg.photo):
                return

    if ai.ready():
        if _cool(("ai", msg.from_user.id), AI_USER_COOLDOWN) and not addressed:
            return
        image = None
        if msg.photo and db.flag("ai_vision"):
            try:
                buf = await bot.download(msg.photo[-1])
                image = buf.read() if buf else None
            except Exception:
                image = None
        context = None
        if msg.reply_to_message and not reply_to_bot:
            context = msg.reply_to_message.text or msg.reply_to_message.caption
        if await ai_reply(msg, bot, text, image, context):
            return

    # 🧠 مغز داخلی (بدون نیاز به کلید)
    if not db.flag("brain_on"):
        return
    res = brain.think(text, msg.from_user.first_name or "دوست من")
    if res:
        body, g = res
        key = ("b", msg.chat.id, body[:40])
        if not addressed and _cool(key, COOLDOWN):
            return
        extra = [B(f"📖 {g['title']}", cb=f"g:{g['id']}")] if g else None
        await msg.reply(body, reply_markup=back_to_menu_kb(extra))
    elif addressed:
        await msg.reply(
            "🤖 من درباره <b>پنل، Railway، GitHub و کانفیگ</b> کمک می‌کنم.\n"
            "📝 مشکلت رو کامل‌تر بنویس یا <b>متن خطا</b> رو بفرست، یا از فهرست انتخاب کن 👇",
            reply_markup=guides_menu_kb(),
        )
