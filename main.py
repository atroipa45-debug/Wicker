import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeChat, BotCommandScopeDefault

import ai
import db
import utils
from config import ADMIN_IDS, BOT_TOKEN, PROXY
import admin
import common
import group
import mod
import user
from middlewares import GroupGuard


async def set_commands(bot: Bot):
    await bot.set_my_commands([BotCommand(command="start", description="شروع")], scope=BotCommandScopeDefault())
    await bot.set_my_commands(
        [BotCommand(command="guide", description="📚 راهنمای پنل، Railway و GitHub")],
        scope=BotCommandScopeAllGroupChats(),
    )
    for aid in ADMIN_IDS:
        try:
            await bot.set_my_commands(
                [
                    BotCommand(command="admin", description="👑 پنل مدیریت"),
                    BotCommand(command="cancel", description="❎ لغو عملیات"),
                ],
                scope=BotCommandScopeChat(chat_id=aid),
            )
        except Exception:
            pass  # ادمین هنوز ربات را استارت نکرده


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not BOT_TOKEN or not ADMIN_IDS:
        raise SystemExit("BOT_TOKEN و ADMIN_IDS تنظیم نشده‌اند. در Railway: سرویس ← Variables، یا در فایل .env")
    db.init()
    session = AiohttpSession(proxy=PROXY) if PROXY else None
    bot = Bot(BOT_TOKEN, session=session,
              default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True))
    dp = Dispatcher()
    guard = GroupGuard()
    dp.message.outer_middleware(guard)
    dp.edited_message.outer_middleware(guard)
    dp.include_routers(admin.router, mod.router, common.router, user.router, group.router)
    me = await bot.me()
    utils.BOT_USERNAME = me.username or ""
    try:
        await set_commands(bot)
        await admin.apply_profile(bot)
    except Exception as e:
        logging.warning("startup setup skipped: %s", e)
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(), handle_as_tasks=True)
    finally:
        await ai.close()


if __name__ == "__main__":
    try:
        import uvloop  # سریع‌تر روی لینوکس
        uvloop.install()
    except ImportError:
        pass
    asyncio.run(main())
