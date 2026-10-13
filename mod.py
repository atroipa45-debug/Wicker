"""دستورهای مدیریتی در گروه: سکوت، بن، اخراج، آزاد کردن، حذف پیام، قفل گروه.
مثال‌ها (ریپلای روی کاربر یا با آیدی):
  سکوت ۱۵        سکوت @user 10 دقیقه        سکوت 123456789 2 ساعت       سکوت (همیشگی)
  بن             بنش کن ۱ روز               اخراج                       آزاد / رفع سکوت / رفع بن
  پاک (ریپلای)   قفل گروه / باز کردن گروه
"""
import asyncio
import html
import re
import time

from aiogram import Bot, F, Router
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, ChatPermissions, Message

import db
from filters import human_duration, parse_duration  # noqa: F401  (parse_duration از بیرون هم استفاده می‌شود)
from utils import GREEN, RED, B, delete_later, is_admin, kb, mention

router = Router(name="mod")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

_FIX = str.maketrans({"آ": "ا", "ي": "ی", "ك": "ک", "\u200c": " "})
CMDS = [
    ("unban", re.compile(r"^/?(?:انبن|ان بن|رفع بن|حذف بن|انبلاک|unban)(?:@\w+)?(?:\s|$)", re.I)),
    ("unmute", re.compile(r"^/?(?:ازاد|رفع سکوت|حذف سکوت|انمیوت|ان میوت|unmute)(?:@\w+)?(?:\s|$)", re.I)),
    ("ban", re.compile(r"^/?(?:بن|بنش|بنش کن|بن کن|مسدود|بلاک|ban)(?:@\w+)?(?:\s|$)", re.I)),
    ("mute", re.compile(r"^/?(?:سکوت|ساکت|میوت|خفه|mute)(?:@\w+)?(?:\s|$)", re.I)),
    ("kick", re.compile(r"^/?(?:اخراج|کیک|ریمو|kick)(?:@\w+)?(?:\s|$)", re.I)),
    ("del", re.compile(r"^/?(?:پاک|حذف|del)(?:@\w+)?$", re.I)),
    ("lock", re.compile(r"^/?(?:قفل گروه|بستن گروه|lock)$", re.I)),
    ("unlock", re.compile(r"^/?(?:باز کردن گروه|بازکردن گروه|باز شدن گروه|unlock)$", re.I)),
]
NO_SEND = ChatPermissions(
    can_send_messages=False, can_send_audios=False, can_send_documents=False, can_send_photos=False,
    can_send_videos=False, can_send_video_notes=False, can_send_voice_notes=False, can_send_polls=False,
    can_send_other_messages=False, can_add_web_page_previews=False,
)
ALL_SEND = ChatPermissions(
    can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True,
    can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True,
    can_send_other_messages=True, can_add_web_page_previews=True, can_invite_users=True,
)


def detect(text: str) -> str | None:
    t = (text or "").translate(_FIX).strip().lower()
    for name, rx in CMDS:
        if rx.match(t):
            return name
    return None


async def can_moderate(bot: Bot, chat_id: int, user_id: int) -> bool:
    if is_admin(user_id):
        return True
    try:
        m = await bot.get_chat_member(chat_id, user_id)
    except Exception:
        return False
    st = getattr(m.status, "value", m.status)
    return st == "creator" or (st == "administrator" and bool(getattr(m, "can_restrict_members", False)))


class ModCommand(BaseFilter):
    async def __call__(self, msg: Message, bot: Bot) -> bool | dict:
        if not msg.text or msg.from_user is None:
            return False
        cmd = detect(msg.text)
        if not cmd:
            return False
        if not await can_moderate(bot, msg.chat.id, msg.from_user.id):
            return False
        return {"cmd": cmd}


async def resolve_target(msg: Message, bot: Bot, use_reply: bool = True):
    """(user_id, نمایش) از ریپلای، پیام فورواردی، منشن، @یوزرنیم یا آیدی عددی."""
    rep = msg.reply_to_message
    if rep is not None:
        origin = getattr(rep, "forward_origin", None)
        if origin is not None and getattr(origin, "type", "") == "user" and getattr(origin, "sender_user", None):
            u = origin.sender_user
            return u.id, mention(u)
        if use_reply and rep.from_user and not rep.from_user.is_bot:
            u = rep.from_user
            return u.id, mention(u)
    for e in msg.entities or []:
        if e.type == "text_mention" and e.user:
            return e.user.id, mention(e.user)
    m = re.search(r"@([A-Za-z][A-Za-z0-9_]{3,31})", msg.text or "")
    if m:
        uid = db.find_user(m.group(1))
        if uid is None:
            try:
                ch = await bot.get_chat("@" + m.group(1))
                uid = ch.id if ch.type == "private" else None
            except Exception:
                uid = None
        if uid:
            return uid, f"@{m.group(1)}"
        return None, f"@{m.group(1)}"
    m = re.search(r"(?<!\d)(\d{6,15})(?!\d)", (msg.text or "").translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")))
    if m:
        uid = int(m.group(1))
        return uid, f'<a href="tg://user?id={uid}">{uid}</a>'
    return None, None


async def _protected(bot: Bot, chat_id: int, uid: int) -> bool:
    if is_admin(uid) or uid == bot.id:
        return True
    try:
        m = await bot.get_chat_member(chat_id, uid)
        return getattr(m.status, "value", m.status) in ("creator", "administrator")
    except Exception:
        return False


def _until(sec: int | None) -> int | None:
    if not sec:
        return None
    sec = max(31, min(sec, 365 * 86400))
    return int(time.time()) + sec


async def apply(bot: Bot, chat_id: int, cmd: str, uid: int, sec: int | None) -> None:
    if cmd == "mute":
        await bot.restrict_chat_member(chat_id, uid, permissions=NO_SEND, until_date=_until(sec),
                                       use_independent_chat_permissions=True)
    elif cmd == "unmute":
        perms = None
        try:
            perms = (await bot.get_chat(chat_id)).permissions
        except Exception:
            pass
        await bot.restrict_chat_member(chat_id, uid, permissions=perms or ALL_SEND, use_independent_chat_permissions=True)
    elif cmd == "ban":
        await bot.ban_chat_member(chat_id, uid, until_date=_until(sec), revoke_messages=False)
    elif cmd == "unban":
        await bot.unban_chat_member(chat_id, uid, only_if_banned=True)
    elif cmd == "kick":
        await bot.ban_chat_member(chat_id, uid)
        await asyncio.sleep(0.5)
        await bot.unban_chat_member(chat_id, uid, only_if_banned=True)


def result_text(cmd: str, who: str, sec: int | None, by: str = "") -> tuple[str, list]:
    d = human_duration(sec)
    by_line = f"\n👮 توسط: {by}" if by else ""
    if cmd == "mute":
        return (f"🔇 <b>سکوت شد</b>\n━━━━━━━━━━━━━━━\n👤 کاربر: {who}\n⏱ مدت: <b>{d}</b>{by_line}",
                "unmute")
    if cmd == "ban":
        return (f"⛔️ <b>بن شد</b>\n━━━━━━━━━━━━━━━\n👤 کاربر: {who}\n⏱ مدت: <b>{d}</b>{by_line}", "unban")
    if cmd == "kick":
        return f"👢 <b>اخراج شد</b>\n━━━━━━━━━━━━━━━\n👤 کاربر: {who}{by_line}", ""
    if cmd == "unmute":
        return f"🔊 <b>سکوت برداشته شد</b>\n👤 کاربر: {who}{by_line}", ""
    if cmd == "unban":
        return f"♻️ <b>رفع بن شد</b>\n👤 کاربر: {who}\n💡 حالا می‌تواند دوباره عضو شود.{by_line}", ""
    return "✅ انجام شد", ""


@router.message(ModCommand())
async def mod_cmd(msg: Message, bot: Bot, cmd: str):
    chat_id = msg.chat.id

    async def drop_cmd():
        try:
            await msg.delete()
        except Exception:
            pass

    if cmd == "del":
        await drop_cmd()
        if msg.reply_to_message:
            try:
                await msg.reply_to_message.delete()
            except Exception:
                pass
        return
    if cmd in ("lock", "unlock"):
        await drop_cmd()
        try:
            await bot.set_chat_permissions(chat_id, NO_SEND if cmd == "lock" else ALL_SEND,
                                           use_independent_chat_permissions=True)
            text = "🔒 <b>گروه قفل شد.</b>\nفقط ادمین‌ها می‌توانند پیام بدهند." if cmd == "lock" else \
                "🔓 <b>گروه باز شد.</b>\nهمه می‌توانند پیام بدهند."
        except Exception:
            text = "⚠️ ربات دسترسی تغییر تنظیمات گروه را ندارد."
        await bot.send_message(chat_id, text)
        return

    uid, who = await resolve_target(msg, bot)
    if uid is None:
        if not who and len((msg.text or "").split()) > 4:
            return  # احتمالاً جمله عادی ادمین است، نه دستور
        hint = (f"⚠️ کاربر {who} را نمی‌شناسم؛ روی پیامش ریپلای کن یا آیدی عددی‌اش را بنویس." if who else
                "⚠️ روی پیام کاربر <b>ریپلای</b> کن یا آیدی‌اش را بنویس.\nمثال: <code>سکوت 15</code> یا <code>بن @user</code>")
        w = await bot.send_message(chat_id, hint)
        asyncio.create_task(delete_later(w, 20))
        return
    if cmd in ("mute", "ban", "kick") and await _protected(bot, chat_id, uid):
        w = await bot.send_message(chat_id, "🛡 این کاربر ادمین است و نمی‌شود محدودش کرد.")
        asyncio.create_task(delete_later(w, 15))
        return

    await drop_cmd()
    sec = parse_duration(re.sub(r"@\w+", " ", msg.text or "")) if cmd in ("mute", "ban") else None
    try:
        await apply(bot, chat_id, cmd, uid, sec)
    except Exception as e:
        w = await bot.send_message(chat_id, f"⚠️ انجام نشد. ربات باید ادمین با دسترسی «محدود کردن کاربران» باشد.\n"
                                            f"<code>{html.escape(str(e))[:120]}</code>")
        asyncio.create_task(delete_later(w, 25))
        return
    if msg.reply_to_message and cmd in ("ban", "kick"):
        try:
            await msg.reply_to_message.delete()
        except Exception:
            pass
    text, undo = result_text(cmd, who, sec, mention(msg.from_user))
    rows = []
    if undo == "unmute":
        rows.append([B("🔊 رفع سکوت", cb=f"m:unmute:{uid}", style=GREEN)])
    elif undo == "unban":
        rows.append([B("♻️ رفع بن", cb=f"m:unban:{uid}", style=GREEN)])
    out = await bot.send_message(chat_id, text, reply_markup=kb(rows) if rows else None)
    asyncio.create_task(delete_later(out, 180))


@router.callback_query(F.data.startswith("m:"))
async def cb_undo(cb: CallbackQuery, bot: Bot):
    if not await can_moderate(bot, cb.message.chat.id, cb.from_user.id):
        await cb.answer("⛔️ فقط ادمین‌ها می‌توانند.", show_alert=True)
        return
    _, cmd, uid = cb.data.split(":")
    try:
        await apply(bot, cb.message.chat.id, cmd, int(uid), None)
    except Exception:
        await cb.answer("⚠️ انجام نشد.", show_alert=True)
        return
    text, _ = result_text(cmd, f'<a href="tg://user?id={uid}">{uid}</a>', None, mention(cb.from_user))
    try:
        await cb.message.edit_text(text)
    except Exception:
        pass
    await cb.answer("✅ انجام شد")
