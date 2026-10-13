"""نگهبان گروه. ترتیب: جعل هویت ← لینک ← تبلیغ ← دعوت به پیوی ← فحش ← فوروارد ← بررسی هوشمند ← جوین اجباری.
همه حذف‌ها بی‌صدا و فوری انجام می‌شوند."""
import asyncio
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

import ai, db
from filters import has_bad_word, is_ad, is_impersonator, is_pv_spam, message_has_bad_link, suspicious
from utils import (
    brand, delete_later, is_admin, is_group_admin, join_kb, join_text, missing_channels, protected_names, support,
)

_warned: dict[tuple[int, int], float] = {}
_fake_cache: dict[int, tuple[float, bool]] = {}
WARN_COOLDOWN = 30
WARN_LIFETIME = 45
SERVICE_FIELDS = (
    "new_chat_members", "left_chat_member", "new_chat_title", "new_chat_photo", "delete_chat_photo", "pinned_message",
    "group_chat_created", "supergroup_chat_created", "migrate_from_chat_id", "migrate_to_chat_id",
    "video_chat_started", "video_chat_ended", "video_chat_scheduled", "video_chat_participants_invited",
    "message_auto_delete_timer_changed", "forum_topic_created", "boost_added",
)


async def _delete(msg: Message, counter: str):
    try:
        await msg.delete()
        db.bump(counter)
    except Exception:
        pass


def fake_user(user) -> bool:
    now = time.time()
    c = _fake_cache.get(user.id)
    if c and now - c[0] < 600:
        return c[1]
    res = is_impersonator(user, protected_names(), [brand(), "سوپر جینکس", "superjinx"])
    _fake_cache[user.id] = (now, res)
    return res


def _own_channel_ids() -> set[int]:
    out = set()
    for ch in db.list_channels():
        try:
            out.add(int(ch["chat_id"]))
        except ValueError:
            pass
    return out


class GroupGuard(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if event.chat.type not in ("group", "supergroup"):
            return await handler(event, data)
        if any(getattr(event, f, None) for f in SERVICE_FIELDS):
            return await handler(event, data)

        bot = data["bot"]
        db.upsert_group(event.chat.id, event.chat.title or str(event.chat.id))
        user = event.from_user

        # پست خودکار کانال متصل و ادمین ناشناس گروه معاف‌اند
        if event.is_automatic_forward or (event.sender_chat and event.sender_chat.id == event.chat.id):
            return await handler(event, data)
        real_user = user is not None and event.sender_chat is None
        if real_user:
            db.remember_user(user.username, user.id)
            if is_admin(user.id) or await is_group_admin(bot, event.chat.id, user.id):
                return await handler(event, data)

        text = event.text or event.caption or ""
        allow = (support(), *protected_names())

        # 🎭 جعل هویت ربات، پشتیبانی یا برند ← حذف و بن
        if real_user and db.flag("anti_fake") and fake_user(user):
            await _delete(event, "del_fake")
            try:
                await bot.ban_chat_member(event.chat.id, user.id)
            except Exception:
                pass
            return None

        # 📢 پیام از طرف کانال دیگر (ارسال با هویت کانال) = تبلیغ
        if event.sender_chat and event.sender_chat.id != event.chat.id and db.flag("f_ads"):
            if event.sender_chat.id not in _own_channel_ids():
                await _delete(event, "del_ads")
                return None

        # 🔗 لینک
        if db.flag("f_links") and message_has_bad_link(event, [event.chat.username, *allow]):
            await _delete(event, "del_links")
            return None
        # 🤖 پیام از طریق ربات اینلاین دیگر یا دکمه شیشه‌ای
        if db.flag("f_ads") and event.via_bot and event.via_bot.id != bot.id:
            await _delete(event, "del_ads")
            return None
        # 💰 تبلیغ
        if db.flag("f_ads") and is_ad(text, allow):
            await _delete(event, "del_ads")
            return None
        # 🚫 دعوت به پیوی و بیو
        if db.flag("f_pv") and is_pv_spam(text, allow):
            await _delete(event, "del_pv")
            return None
        # 🤬 فحش و تهدید
        if db.flag("f_bad") and has_bad_word(text):
            await _delete(event, "del_bad")
            return None
        # 📨 فوروارد از کانال یا گروه دیگر (به‌جز کانال‌های خودمان)
        origin = getattr(event, "forward_origin", None)
        if db.flag("f_fwd") and origin is not None:
            otype = getattr(origin, "type", "")
            ochat = getattr(origin, "chat", None) or getattr(origin, "sender_chat", None)
            if otype in ("channel", "chat") and not (ochat and ochat.id in _own_channel_ids()):
                await _delete(event, "del_fwd")
                return None
        # 📖 استوری فورواردی هم تبلیغ حساب می‌شود
        if db.flag("f_ads") and getattr(event, "story", None):
            await _delete(event, "del_ads")
            return None

        # 🧠 بررسی هوشمند پیام‌های مشکوک (فقط اگر هوش مصنوعی ابری فعال باشد)
        if (db.flag("ai_mod") and ai.ready() and len(text) >= 3 and suspicious(text)
                and support().lower() not in text.lower()):
            if await ai.should_delete(text):
                await _delete(event, "del_ai")
                return None

        if data.get("event_update") is not None and data["event_update"].edited_message is not None:
            return await handler(event, data)

        # 🔐 جوین اجباری
        if not real_user or user.is_bot:
            return await handler(event, data)
        missing = await missing_channels(bot, user.id)
        if not missing:
            return await handler(event, data)
        try:
            await event.delete()
        except Exception:
            pass
        key = (event.chat.id, user.id)
        if time.time() - _warned.get(key, 0) > WARN_COOLDOWN:
            _warned[key] = time.time()
            try:
                warn = await bot.send_message(event.chat.id, join_text(user), reply_markup=join_kb(missing, user.id))
                asyncio.create_task(delete_later(warn, WARN_LIFETIME))
            except Exception:
                pass
        return None
