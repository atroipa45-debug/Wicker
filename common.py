"""کال‌بک‌های گروه: منوی راهنما و دکمه «عضو شدم»."""
import html

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery

import db
from utils import back_to_menu_kb, brand, clear_join_cache, guides_menu_kb, missing_channels

router = Router(name="common")

def menu_text() -> str:
    return (
        f"📚 <b>راهنمای {html.escape(brand())}</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🚂 Railway  •  🐙 GitHub  •  ⚡️ پنل  •  🧬 کانفیگ\n\n"
        "💬 سؤالت را بنویس یا متن خطا را بفرست؛ جینکس جواب می‌دهد.\n"
        "👇 یا موضوعت را انتخاب کن"
    )


@router.callback_query(F.data.startswith("fj:chk:"))
async def cb_check_join(cb: CallbackQuery, bot: Bot):
    owner = int(cb.data.split(":")[2])
    if owner and owner != cb.from_user.id:
        await cb.answer("⛔️ این دکمه برای شما نیست.", show_alert=True)
        return
    clear_join_cache(cb.from_user.id)
    missing = await missing_channels(bot, cb.from_user.id)
    if missing:
        await cb.answer("❌ هنوز عضو همه کانال‌ها نشدی.", show_alert=True)
        return
    await cb.answer("✅ عضویت تأیید شد، خوش اومدی!", show_alert=True)
    if cb.message.chat.type == "private":
        try:
            await cb.message.edit_text(menu_text(), reply_markup=guides_menu_kb())
        except Exception:
            pass
        return
    try:
        await cb.message.delete()
    except Exception:
        pass


@router.callback_query(F.data.startswith("g:"))
async def cb_guide(cb: CallbackQuery):
    key = cb.data.split(":", 1)[1]
    try:
        if key == "menu":
            await cb.message.edit_text(menu_text(), reply_markup=guides_menu_kb())
        else:
            g = db.get_guide(int(key))
            if not g:
                await cb.answer("این راهنما حذف شده است.", show_alert=True)
                return
            await cb.message.edit_text(g["body"], reply_markup=back_to_menu_kb())
    except Exception:
        pass  # پیام تغییری نکرده
    await cb.answer()
