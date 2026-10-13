"""پیوی کاربران عادی: کمک به سؤال‌های پنل و کانفیگ + آیدی پشتیبانی. پنل مدیریت فقط برای ادمین."""
import time

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

import ai, brain, db
from filters import wants_to_buy
from utils import (
    B, back_to_menu_kb, buy_text, guides_menu_kb, is_admin, join_kb, missing_channels, support_kb, support_text,
)

router = Router(name="user")
router.message.filter(F.chat.type == "private")
_last: dict[int, float] = {}


async def _gate(msg: Message, bot: Bot) -> bool:
    missing = await missing_channels(bot, msg.from_user.id)
    if missing:
        await msg.answer("🔐 برای استفاده از ربات، اول عضو کانال‌های ما شو 👇\n\n✨ <i>بعد دکمه «عضو شدم» را بزن.</i>",
                         reply_markup=join_kb(missing, msg.from_user.id))
        return False
    return True


@router.message(CommandStart())
async def start(msg: Message, bot: Bot):
    if is_admin(msg.from_user.id):
        await msg.answer("👑 سلام ادمین! برای باز کردن پنل مدیریت: /admin")
        return
    db.touch_user(msg.from_user.id, msg.from_user.full_name)
    if not await _gate(msg, bot):
        return
    await msg.answer(support_text(), reply_markup=support_kb())
    if db.flag("pv_help"):
        await msg.answer("📚 <b>راهنماها</b>\n👇 موضوعت را انتخاب کن یا سؤالت را بنویس", reply_markup=guides_menu_kb())


@router.message()
async def private_any(msg: Message, bot: Bot):
    if is_admin(msg.from_user.id):
        await msg.answer("👑 سلام ادمین! برای باز کردن پنل مدیریت: /admin")
        return
    db.touch_user(msg.from_user.id, msg.from_user.full_name)
    if not db.flag("pv_help"):
        await msg.answer(support_text(), reply_markup=support_kb())
        return
    if not await _gate(msg, bot):
        return
    now = time.time()
    if now - _last.get(msg.from_user.id, 0) < 2:
        return  # ضد اسپم
    _last[msg.from_user.id] = now
    text = msg.text or msg.caption or ""
    if wants_to_buy(text):
        await msg.answer(buy_text(msg.from_user), reply_markup=support_kb())
        return

    if ai.ready() and text:
        try:
            await bot.send_chat_action(msg.chat.id, "typing")
            out = await ai.answer(msg.chat.id, msg.from_user.id, msg.from_user.first_name or "کاربر", text)
            body, tags = ai.render(out)
            extra = []
            for kind, i in tags:
                if kind == "link" and (l := db.get_link(i)):
                    extra.append(B(l["title"], url=l["url"]))
                elif kind == "guide" and (g := db.get_guide(i)):
                    extra.append(B(f"📖 {g['title']}", cb=f"g:{g['id']}"))
            try:
                await msg.answer(body, reply_markup=back_to_menu_kb(extra))
            except Exception:
                await msg.answer(ai.TAG_RE.sub("", out)[:4000], reply_markup=back_to_menu_kb(extra), parse_mode=None)
            return
        except Exception:
            pass

    res = brain.think(text, msg.from_user.first_name or "دوست من") if text else None
    if res:
        body, g = res
        extra = [B(f"📖 {g['title']}", cb=f"g:{g['id']}")] if g else None
        await msg.answer(body, reply_markup=back_to_menu_kb(extra))
    else:
        await msg.answer(support_text(), reply_markup=support_kb())
        await msg.answer("📚 یا از راهنماها انتخاب کن 👇", reply_markup=guides_menu_kb())


@router.callback_query(F.message.chat.type == "private")
async def private_cb(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔️ این بخش فقط برای ادمین است.", show_alert=True)
    else:
        await cb.answer()
