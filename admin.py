import asyncio
import html
import re
import time

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import ai, db
import sub as subm
import utils
from config import ADMIN_IDS, PROXY
import mod
from utils import (
    BLUE, DEFAULT_WELCOME, GREEN, RED, B, chunk, kb, parse_spec, support, support_url, welcome_kb, welcome_text,
)

router = Router(name="admin")
router.message.filter(F.chat.type == "private", F.from_user.id.in_(ADMIN_IDS))
router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS), F.data.startswith("a:"))

LINE = "━━━━━━━━━━━━━━━"


class SG(StatesGroup):
    channel = State()
    post_content = State()
    post_buttons = State()
    g_title = State()
    g_keywords = State()
    g_body = State()
    g_edit = State()
    welcome = State()
    support = State()
    badword = State()
    sub_link = State()
    ai_key = State()
    ai_base = State()
    ai_model = State()
    ai_know = State()
    ai_test = State()
    link_title = State()
    link_url = State()
    link_kw = State()


def back(to="a:home", text="🔙 بازگشت"):
    return [B(text, cb=to, style=BLUE)]


def on_off(key) -> str:
    return "🟢 روشن" if db.flag(key) else "🔴 خاموش"


def tog(label, key, cb):
    return B(f"{label}: {'روشن' if db.flag(key) else 'خاموش'}", cb=cb, style=GREEN if db.flag(key) else RED)


async def show(target, text, markup):
    """اگر کال‌بک بود ویرایش کن، اگر پیام بود پیام جدید بفرست."""
    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=markup)
        except Exception as e:
            if "not modified" not in str(e):
                await target.message.answer(text, reply_markup=markup)
        try:
            await target.answer()
        except Exception:
            pass
    else:
        await target.answer(text, reply_markup=markup)


# ================================================================ خانه
def home():
    c = db.counts()
    ai_state = ("🟢 ابری + مغز داخلی" if ai.ready() else
                "🟢 مغز داخلی فعال" if db.flag("brain_on") else "🔴 خاموش")
    text = (
        f"👑 <b>پنل مدیریت {html.escape(utils.brand())}</b>\n"
        f"{LINE}\n\n"
        f"👥 گروه‌ها: <b>{c['groups']}</b>     📚 راهنماها: <b>{c['guides']}</b>\n"
        f"🧠 هوش مصنوعی: {ai_state}\n"
        f"🔐 جوین اجباری: {on_off('fj_enabled')}     🛡 فیلتر لینک: {on_off('f_links')}\n\n"
        "👇 یک بخش را انتخاب کنید"
    )
    markup = kb([
        [B("➕ افزودن ربات به گروه", url=utils.add_group_url()), B("📢 افزودن به کانال", url=utils.add_channel_url())],
        [B("📣 پیام هماهنگی و پست با دکمه", cb="a:post")],
        [B("💎 معرفی سابلینک در گروه", cb="a:sub")],
        [B("🧠 هوش مصنوعی", cb="a:ai"), B("🔐 جوین اجباری", cb="a:fj")],
        [B("🛡 امنیت و فیلتر", cb="a:sec"), B("🔗 لینک‌های مهم", cb="a:links")],
        [B("📚 راهنماها", cb="a:guides"), B("👋 خوش‌آمدگویی", cb="a:wel")],
        [B("🏷 مشخصات ربات", cb="a:id"), B("👮 دستورهای مدیریت", cb="a:modhelp")],
        [B("💬 آیدی پشتیبانی", cb="a:sup"), B("👥 گروه‌ها", cb="a:groups")],
        [B("📊 آمار", cb="a:stats")],
    ])
    return text, markup


@router.message(Command("admin", "panel", "start"))
async def open_panel(msg: Message, state: FSMContext):
    await state.clear()
    await show(msg, *home())


@router.message(Command("cancel"))
async def cancel(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("❎ لغو شد.")
    await show(msg, *home())


@router.callback_query(F.data == "a:home")
async def cb_home(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await show(cb, *home())


# ================================================================ آمار
@router.callback_query(F.data == "a:stats")
async def cb_stats(cb: CallbackQuery):
    c = db.counts()
    g = lambda k: db.get_setting(k, "0") or "0"
    text = (
        "📊 <b>آمار ربات</b>\n"
        f"{LINE}\n\n"
        f"👥 گروه‌ها: <b>{c['groups']}</b>\n"
        f"📚 راهنماها: <b>{c['guides']}</b>\n"
        f"📢 کانال‌های جوین اجباری: <b>{c['channels']}</b>\n"
        f"🙋 کسانی که پیوی پیام دادند: <b>{c['users']}</b>\n\n"
        f"🔗 لینک‌های حذف‌شده: <b>{g('del_links')}</b>\n"
        f"🤬 فحش و تهدید حذف‌شده: <b>{g('del_bad')}</b>\n"
        f"📨 فوروارد حذف‌شده: <b>{g('del_fwd')}</b>\n"
        f"🚫 دعوت به پیوی و بیو حذف‌شده: <b>{g('del_pv')}</b>\n"
        f"💰 تبلیغ حذف‌شده: <b>{g('del_ads')}</b>\n"
        f"🎭 جعل هویت (بن‌شده): <b>{g('del_fake')}</b>\n"
        f"🧠 حذف‌شده توسط هوش مصنوعی: <b>{g('del_ai')}</b>\n"
        f"💬 درخواست‌های هوش مصنوعی: <b>{g('ai_calls')}</b>"
    )
    await show(cb, text, kb([back()]))


# ================================================================ جوین اجباری
def fj_view():
    chans = db.list_channels()
    lines = ["🔐 <b>جوین اجباری</b>", LINE, "", f"وضعیت: {on_off('fj_enabled')}", ""]
    if chans:
        lines += [f"{i}. 📢 {html.escape(ch['title'])}" for i, ch in enumerate(chans, 1)]
    else:
        lines.append("هنوز کانالی اضافه نشده.")
    rows = [
        [tog("🔘 جوین اجباری", "fj_enabled", "a:fj_toggle")],
        [B("➕ افزودن کانال", cb="a:fj_add", style=GREEN)],
    ]
    rows += [[B(f"🗑 حذف {ch['title']}", cb=f"a:fj_del:{ch['id']}", style=RED)] for ch in chans]
    rows.append(back())
    return "\n".join(lines), kb(rows)


@router.callback_query(F.data == "a:fj")
async def cb_fj(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await show(cb, *fj_view())


@router.callback_query(F.data == "a:fj_toggle")
async def cb_fj_toggle(cb: CallbackQuery):
    db.toggle("fj_enabled")
    await show(cb, *fj_view())


@router.callback_query(F.data.startswith("a:fj_del:"))
async def cb_fj_del(cb: CallbackQuery):
    db.del_channel(int(cb.data.split(":")[2]))
    await show(cb, *fj_view())


@router.callback_query(F.data == "a:fj_add")
async def cb_fj_add(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SG.channel)
    await show(
        cb,
        "➕ <b>افزودن کانال جوین اجباری</b>\n"
        f"{LINE}\n\n"
        "1️⃣ اول ربات را در کانال <b>ادمین</b> کنید.\n"
        "2️⃣ بعد یکی از این‌ها را بفرستید:\n\n"
        "▫️ یوزرنیم: <code>@mychannel</code>\n"
        "▫️ آیدی عددی: <code>-1001234567890</code>\n"
        "▫️ یا یک پست از کانال را فوروارد کنید\n\n"
        "❎ لغو: /cancel",
        kb([back("a:fj")]),
    )


@router.message(StateFilter(SG.channel))
async def fj_receive(msg: Message, state: FSMContext, bot: Bot):
    ident = None
    origin = getattr(msg, "forward_origin", None)
    if origin is not None and getattr(origin, "type", None) == "channel":
        ident = origin.chat.id
    elif msg.text:
        t = msg.text.strip()
        if "t.me/" in t:
            t = "@" + t.rstrip("/").split("/")[-1]
        ident = int(t) if t.lstrip("-").isdigit() else t
    if ident is None:
        await msg.answer("⚠️ ورودی نامعتبر است. دوباره بفرستید یا /cancel")
        return
    try:
        chat = await bot.get_chat(ident)
        me = await bot.get_chat_member(chat.id, bot.id)
        if getattr(me.status, "value", me.status) not in ("administrator", "creator"):
            raise PermissionError
    except PermissionError:
        await msg.answer("⚠️ ربات در این کانال ادمین نیست. اول ادمینش کنید و دوباره بفرستید.")
        return
    except Exception:
        await msg.answer("⚠️ کانال پیدا نشد یا ربات دسترسی ندارد. ربات را ادمین کنید و دوباره امتحان کنید.")
        return
    link = f"https://t.me/{chat.username}" if chat.username else chat.invite_link
    if not link:
        try:
            link = await bot.export_chat_invite_link(chat.id)
        except Exception:
            await msg.answer("⚠️ برای کانال خصوصی، ربات باید دسترسی «ساخت لینک دعوت» داشته باشد.")
            return
    db.add_channel(chat.id, chat.title or str(chat.id), link)
    await state.clear()
    await msg.answer(f"✅ کانال <b>{html.escape(chat.title or '')}</b> اضافه شد.")
    await show(msg, *fj_view())


# ================================================================ امنیت
def sec_view():
    text = (
        "🛡 <b>امنیت و فیلتر گروه</b>\n"
        f"{LINE}\n\n"
        "💰 <b>ضد تبلیغات</b>: فروش کانفیگ و ممبر، قیمت و تومن، شماره تلفن، «عضو کانال ما شید»، پیام با هویت کانال دیگر، "
        "ربات اینلاین و استوری فورواردی بی‌صدا پاک می‌شود.\n"
        "🔗 <b>حذف لینک</b>: لینک کانال و گروه تلگرام و پیام‌رسان‌های دیگر بی‌صدا پاک می‌شود.\n"
        "▫️ آیدی، آیدی ربات، کانفیگ و سابلینک آزاد است.\n\n"
        "🤬 <b>حذف فحش و تهدید</b>: بی‌صدا پاک می‌شود.\n"
        "🚫 <b>دعوت به پیوی و بیو</b>: «بیا پیوی»، «بیومو چک کن»، «کانالم تو بیو» و مشابهش بی‌صدا پاک می‌شود.\n"
        "🧠 <b>تشخیص هوشمند</b>: پیام‌های مشکوکی که فیلتر معمولی نگرفته، با هوش مصنوعی بررسی و پاک می‌شوند.\n"
        "📨 <b>حذف فوروارد</b>: پیام‌های فورواردی از کانال‌ها و گروه‌های دیگر.\n"
        "🛒 <b>ارجاع خرید</b>: هر کس بخواهد پنل یا کانفیگ بخرد، به پشتیبانی ارجاع داده می‌شود.\n"
        "🤖 <b>جواب خودکار</b>: جواب سؤال‌های پنل، Railway و GitHub.\n\n"
        "🎭 <b>ضد جعل هویت</b>: هر کس اسم یا یوزرنیمش شبیه ربات، پشتیبانی یا برند شما باشد، فوراً بن می‌شود.\n"
        "🔒 <b>قفل ضد کپی</b>: اگر کسی غیر از شما ربات را به گروهش اضافه کند، ربات خودکار خارج می‌شود.\n\n"
        "👑 ادمین‌های گروه از همه فیلترها معاف‌اند."
    )
    markup = kb([
        [tog("💰 ضد تبلیغات", "f_ads", "a:t:f_ads")],
        [tog("🔗 حذف لینک", "f_links", "a:t:f_links")],
        [tog("🤬 حذف فحش و تهدید", "f_bad", "a:t:f_bad")],
        [tog("🚫 حذف «بیا پیوی» و «بیومو ببین»", "f_pv", "a:t:f_pv")],
        [tog("🧠 تشخیص هوشمند با هوش مصنوعی", "ai_mod", "a:t:ai_mod")],
        [tog("📨 حذف فوروارد", "f_fwd", "a:t:f_fwd")],
        [tog("🛒 ارجاع خرید", "buy_reply", "a:t:buy_reply")],
        [tog("🤖 جواب خودکار", "auto_answer", "a:t:auto_answer")],
        [tog("🎭 ضد جعل هویت", "anti_fake", "a:t:anti_fake")],
        [tog("🔒 قفل ضد کپی ربات", "lock", "a:t:lock")],
        [tog("🧹 حذف پیام ورود و خروج", "del_service", "a:t:del_service")],
        [B("📝 کلمات ممنوعه دلخواه", cb="a:bw", style=BLUE)],
        back(),
    ], rainbow=False)
    return text, markup


@router.callback_query(F.data == "a:sec")
async def cb_sec(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await show(cb, *sec_view())


@router.callback_query(F.data.startswith("a:t:"))
async def cb_toggle(cb: CallbackQuery):
    key = cb.data.split(":", 2)[2]
    if key in db.DEFAULTS:
        db.toggle(key)
    view = {"welcome_on": wel_view, "ai_on": ai_view, "ai_vision": ai_view, "ai_all": ai_view,
            "brain_on": ai_view, "pv_help": id_view}.get(key, sec_view)
    await show(cb, *view())


def bw_view():
    words = db.list_badwords()
    text = (
        "📝 <b>کلمات ممنوعه دلخواه</b>\n"
        f"{LINE}\n\n"
        "یک لیست کامل فحش و تهدید از قبل داخل ربات هست. اینجا کلمه‌های اضافه خودتان را مدیریت کنید.\n"
        "برای حذف، روی کلمه بزنید.\n\n"
        f"تعداد: <b>{len(words)}</b>"
    )
    btns = [B(f"🗑 {w}", cb=f"a:bw_del:{i}", style=RED) for i, w in enumerate(words[:40])]
    rows = chunk(btns, 3)
    rows.insert(0, [B("➕ افزودن کلمه", cb="a:bw_add", style=GREEN)])
    rows.append(back("a:sec"))
    return text, kb(rows, rainbow=False)


@router.callback_query(F.data == "a:bw")
async def cb_bw(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await show(cb, *bw_view())


@router.callback_query(F.data.startswith("a:bw_del:"))
async def cb_bw_del(cb: CallbackQuery):
    i = int(cb.data.split(":")[2])
    words = db.list_badwords()
    if i < len(words):
        db.del_badword(words[i])
    await show(cb, *bw_view())


@router.callback_query(F.data == "a:bw_add")
async def cb_bw_add(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SG.badword)
    await show(cb, "✍️ کلمه‌ها را بفرستید؛ چندتا را با کاما جدا کنید.\n\nمثال: <code>کلمه۱, کلمه۲</code>\n\n❎ لغو: /cancel",
               kb([back("a:bw")]))


@router.message(StateFilter(SG.badword), F.text)
async def bw_save(msg: Message, state: FSMContext):
    db.add_badwords(msg.text.replace("،", ",").split(","))
    await state.clear()
    await msg.answer("✅ اضافه شد.")
    await show(msg, *bw_view())


# ================================================================ خوش‌آمدگویی
def wel_view():
    text = (
        "👋 <b>خوش‌آمدگویی</b>\n"
        f"{LINE}\n\n"
        f"وضعیت: {on_off('welcome_on')}\n\n"
        "برای عوض کردن متن، از این برچسب‌ها استفاده کنید:\n"
        "<code>{name}</code> اسم کاربر\n<code>{id}</code> آیدی کاربر\n"
        "<code>{group}</code> اسم گروه\n<code>{support}</code> آیدی پشتیبانی\n<code>{brand}</code> اسم برند"
    )
    markup = kb([
        [tog("🔘 خوش‌آمدگویی", "welcome_on", "a:t:welcome_on")],
        [B("👁 پیش‌نمایش", cb="a:wel_prev"), B("✏️ تغییر متن", cb="a:wel_edit")],
        [B("♻️ متن پیش‌فرض", cb="a:wel_reset")],
        back(),
    ])
    return text, markup


@router.callback_query(F.data == "a:wel")
async def cb_wel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await show(cb, *wel_view())


@router.callback_query(F.data == "a:wel_prev")
async def cb_wel_prev(cb: CallbackQuery):
    class _Chat:
        title = "گروه شما"
    await cb.message.answer(welcome_text(cb.from_user, _Chat), reply_markup=welcome_kb())
    await cb.answer()


@router.callback_query(F.data == "a:wel_reset")
async def cb_wel_reset(cb: CallbackQuery):
    db.set_setting("welcome_text", "")
    await cb.answer("♻️ متن پیش‌فرض برگشت", show_alert=True)


@router.callback_query(F.data == "a:wel_edit")
async def cb_wel_edit(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SG.welcome)
    await cb.message.answer("✏️ متن جدید خوش‌آمدگویی را بفرستید (بولد و ایموجی مجاز است).\n\n<b>متن فعلی:</b>")
    await cb.message.answer(html.escape(db.get_setting("welcome_text") or DEFAULT_WELCOME))
    await cb.answer()


@router.message(StateFilter(SG.welcome), F.text)
async def wel_save(msg: Message, state: FSMContext):
    db.set_setting("welcome_text", msg.html_text)
    await state.clear()
    await msg.answer("✅ متن خوش‌آمدگویی ذخیره شد.")
    await show(msg, *wel_view())


# ================================================================ پشتیبانی
@router.callback_query(F.data == "a:sup")
async def cb_sup(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SG.support)
    await show(
        cb,
        "💬 <b>آیدی پشتیبانی</b>\n"
        f"{LINE}\n\n"
        f"آیدی فعلی: {support()}\n\n"
        "این آیدی به کسانی که پیوی پیام می‌دهند یا در گروه قصد خرید دارند نشان داده می‌شود.\n\n"
        "✍️ برای تغییر، آیدی جدید را بفرستید (مثل <code>@SuperJinx2</code>).",
        kb([back()]),
    )


@router.message(StateFilter(SG.support), F.text)
async def sup_save(msg: Message, state: FSMContext):
    s = msg.text.strip().split()[0]
    if "t.me/" in s:
        s = s.rstrip("/").split("/")[-1]
    s = "@" + s.lstrip("@")
    db.set_setting("support", s)
    await state.clear()
    await msg.answer(f"✅ آیدی پشتیبانی شد: {s}")
    await show(msg, *home())


# ================================================================ گروه‌ها
def groups_view():
    groups = db.list_groups()
    if groups:
        text = "👥 <b>گروه‌ها</b>\n" + LINE + "\n\nبرای حذف از لیست روی گروه بزنید."
    else:
        text = "👥 ربات هنوز در گروهی نیست.\nربات را به گروه اضافه و <b>ادمین</b> کنید."
    rows = [[B(f"🗑 {g['title']}", cb=f"a:grp_del:{g['chat_id']}")] for g in groups]
    rows.append(back())
    return text, kb(rows)


@router.callback_query(F.data == "a:groups")
async def cb_groups(cb: CallbackQuery):
    await show(cb, *groups_view())


@router.callback_query(F.data.startswith("a:grp_del:"))
async def cb_grp_del(cb: CallbackQuery):
    db.del_group(int(cb.data.split(":", 2)[2]))
    await show(cb, *groups_view())


# ================================================================ پیام هماهنگی و پست
@router.callback_query(F.data == "a:post")
async def cb_post(cb: CallbackQuery, state: FSMContext):
    if not db.list_groups():
        await cb.answer("⚠️ ربات هنوز در هیچ گروهی نیست. اول از «افزودن ربات به گروه» استفاده کنید.", show_alert=True)
        return
    await state.set_state(SG.post_content)
    await show(
        cb,
        "📣 <b>پیام هماهنگی و پست با دکمه</b>\n"
        f"{LINE}\n\n"
        "1️⃣ متن پیام را بفرستید (عکس، ویدیو و فایل با کپشن هم قبول است).\n\n"
        "💡 مثال: <i>امروز ساعت ۹ شب آموزش نصب پنل Super JinX روی Railway را می‌گذاریم 🔥</i>\n\n"
        "❎ لغو: /cancel",
        kb([back()]),
    )


@router.message(StateFilter(SG.post_content))
async def post_content(msg: Message, state: FSMContext):
    await state.update_data(src_chat=msg.chat.id, src_msg=msg.message_id, spec=None)
    await state.set_state(SG.post_buttons)
    await msg.answer(
        "2️⃣ <b>دکمه‌های لینک‌دار را بفرستید</b>\n\n"
        "▫️ هر خط یک ردیف\n▫️ هر دکمه: <code>متن | لینک</code>\n"
        "▫️ چند دکمه در یک ردیف: با <code>&amp;&amp;</code>\n\n"
        "مثال:\n<code>🚂 آموزش Railway | https://t.me/mychannel/12\n"
        "🐙 گیتهاب | https://github.com/xxx &amp;&amp; 💬 پشتیبانی | https://t.me/SuperJinx2</code>\n\n"
        "🌈 دکمه‌ها خودکار رنگی می‌شوند.",
        reply_markup=kb([
            [B("⏭ بدون دکمه", cb="a:post_nobtn"), B("💬 فقط دکمه پشتیبانی", cb="a:post_supbtn")],
            [B("❌ لغو", cb="a:home", style=RED)],
        ]),
    )


async def preview(bot: Bot, chat_id: int, state: FSMContext):
    data = await state.get_data()
    spec = data.get("spec")
    await bot.copy_message(chat_id, data["src_chat"], data["src_msg"], reply_markup=kb(spec) if spec else None)
    groups = db.list_groups()
    rows = []
    if len(groups) > 1:
        rows.append([B(f"📣 ارسال به همه ({len(groups)} گروه)", cb="a:ps:all:0"), B("📣📌 همه + سنجاق", cb="a:ps:all:1")])
    for g in groups:
        rows.append([B(f"📤 {g['title']}", cb=f"a:ps:{g['chat_id']}:0"), B("📌 ارسال و سنجاق", cb=f"a:ps:{g['chat_id']}:1")])
    rows.append([B("❌ لغو", cb="a:home", style=RED)])
    await bot.send_message(chat_id, "👆 <b>پیش‌نمایش</b>\nکجا ارسال شود؟", reply_markup=kb(rows))


@router.message(StateFilter(SG.post_buttons), F.text)
async def post_buttons(msg: Message, state: FSMContext, bot: Bot):
    try:
        spec = parse_spec(msg.text)
    except ValueError as e:
        await msg.answer(f"⚠️ این خط درست نیست:\n<code>{html.escape(str(e))}</code>\nدوباره بفرستید.")
        return
    await state.update_data(spec=spec or None)
    await preview(bot, msg.chat.id, state)


@router.callback_query(F.data.in_({"a:post_nobtn", "a:post_supbtn"}), StateFilter(SG.post_buttons))
async def cb_post_nobtn(cb: CallbackQuery, state: FSMContext, bot: Bot):
    spec = [[B("💬 پیام به پشتیبانی", url=support_url())]] if cb.data == "a:post_supbtn" else None
    await state.update_data(spec=spec)
    await cb.answer()
    await preview(bot, cb.message.chat.id, state)


@router.callback_query(F.data.startswith("a:ps:"))
async def cb_post_send(cb: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    if "src_msg" not in data:
        await cb.answer("⚠️ پیامی برای ارسال نیست. از اول شروع کنید.", show_alert=True)
        return
    _, _, target, pin = cb.data.split(":")
    targets = [g["chat_id"] for g in db.list_groups()] if target == "all" else [int(target)]
    spec = data.get("spec")
    await cb.answer("⏳ در حال ارسال...")
    ok, fail, nopin = 0, 0, 0
    for chat_id in targets:
        try:
            sent = await bot.copy_message(chat_id, data["src_chat"], data["src_msg"], reply_markup=kb(spec) if spec else None)
            ok += 1
            if pin == "1":
                try:
                    await bot.pin_chat_message(chat_id, sent.message_id)
                except Exception:
                    nopin += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.07)
    await state.clear()
    text = f"✅ <b>انجام شد</b>\n\n📤 ارسال موفق: <b>{ok}</b>"
    if fail:
        text += f"\n⚠️ ناموفق: <b>{fail}</b> (ربات دسترسی ارسال ندارد)"
    if nopin:
        text += f"\n📌 سنجاق نشد: <b>{nopin}</b> (ربات دسترسی سنجاق ندارد)"
    try:
        await cb.message.edit_text(text, reply_markup=kb([back(text="🏠 پنل مدیریت")]))
    except Exception:
        await cb.message.answer(text, reply_markup=kb([back(text="🏠 پنل مدیریت")]))


# ================================================================ معرفی سابلینک
@router.callback_query(F.data == "a:sub")
async def cb_sub(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SG.sub_link)
    await show(
        cb,
        "💎 <b>معرفی سابلینک در گروه</b>\n"
        f"{LINE}\n\n"
        "سابلینک را بفرستید؛ ربات خودش آن را می‌خواند و یک کارت معرفی شیک می‌سازد:\n\n"
        "📡 تعداد کانفیگ‌ها   🧬 پروتکل‌ها   🛰 نوع شبکه\n"
        "🌍 لوکیشن‌ها   📊 حجم و مصرف   ⏳ تاریخ انقضا (شمسی)\n"
        "🧠 متن معرفی جذاب با هوش مصنوعی\n"
        "📋 دکمه کپی سابلینک با یک لمس\n\n"
        "❎ لغو: /cancel",
        kb([back()]),
    )


async def build_sub(bot: Bot, chat_id: int, state: FSMContext, url: str, regen: bool = False):
    wait = await bot.send_message(chat_id, "⏳ <b>در حال خواندن سابلینک...</b>")
    try:
        data = await subm.fetch(url, PROXY)
    except Exception as e:
        await wait.edit_text(
            "⚠️ <b>سابلینک خوانده نشد.</b>\n\n"
            "▫️ لینک را کامل و درست بفرستید (با https://)\n"
            "▫️ سرویس فعال باشد و منقضی نشده باشد\n"
            f"▫️ خطا: <code>{html.escape(str(e))[:150]}</code>\n\n"
            "دوباره بفرستید یا /cancel"
        )
        return
    _, summary = subm.card(data)
    intro = await ai.sub_intro(summary) if ai.ready() else ""
    if intro:
        intro, _ = ai.render(intro)
    else:
        intro = "🚀 <b>سرعت بالا، اتصال پایدار، بدون قطعی</b>\n✨ مناسب همه اپراتورها و همه دستگاه‌ها"
    text, _ = subm.card(data, intro)
    spec = [[B("📋 کپی سابلینک", copy=url)] if len(url) <= 256 else [B("🔗 سابلینک", url=url)]]
    if url.startswith("http"):
        spec.append([B("🌐 صفحه اشتراک", url=url)])
    spec.append([B("📱 آموزش اتصال", cb="g:menu"), B("💬 پشتیبانی", url=support_url())])
    try:
        await wait.delete()
    except Exception:
        pass
    card_msg = await bot.send_message(chat_id, text, reply_markup=kb(spec))
    await state.set_state(None)
    await state.update_data(src_chat=chat_id, src_msg=card_msg.message_id, spec=spec, sub_url=url)
    groups = db.list_groups()
    rows = [[B("🔄 متن جدید با هوش مصنوعی", cb="a:sub_regen")]] if ai.ready() else []
    if len(groups) > 1:
        rows.append([B(f"📣 ارسال به همه ({len(groups)} گروه)", cb="a:ps:all:0"), B("📣📌 همه + سنجاق", cb="a:ps:all:1")])
    for g in groups:
        rows.append([B(f"📤 {g['title']}", cb=f"a:ps:{g['chat_id']}:0"), B("📌 ارسال و سنجاق", cb=f"a:ps:{g['chat_id']}:1")])
    rows.append([B("❌ لغو", cb="a:home", style=RED)])
    note = "" if groups else "\n⚠️ ربات هنوز در گروهی نیست."
    await bot.send_message(chat_id, f"👆 <b>کارت معرفی آماده است.</b>\nکجا ارسال شود؟{note}", reply_markup=kb(rows))


@router.message(StateFilter(SG.sub_link), F.text)
async def sub_receive(msg: Message, state: FSMContext, bot: Bot):
    url = msg.text.strip().split()[0]
    if not url.startswith(("http://", "https://")):
        await msg.answer("⚠️ سابلینک باید با <code>https://</code> شروع شود. دوباره بفرستید.")
        return
    await build_sub(bot, msg.chat.id, state, url)


@router.callback_query(F.data == "a:sub_regen")
async def cb_sub_regen(cb: CallbackQuery, state: FSMContext, bot: Bot):
    url = (await state.get_data()).get("sub_url")
    if not url:
        await cb.answer("⚠️ سابلینک را دوباره بفرستید.", show_alert=True)
        return
    await cb.answer("🔄 ساخت متن جدید...")
    await build_sub(bot, cb.message.chat.id, state, url)


# ================================================================ هوش مصنوعی
def ai_view():
    c = ai.cfg()
    key = c["key"]
    masked = (key[:4] + "•••" + key[-4:]) if len(key) > 10 else ("ثبت شده" if key else "❌ ندارد")
    preset = next((v[0] for v in ai.PRESETS.values() if v[1] == c["base"]), c["base"] or "❌ انتخاب نشده")
    status = "🟢 آماده" if ai.ready() else ("🔴 خاموش" if not db.flag("ai_on") else "⚪️ کلید ثبت نشده")
    text = (
        "🧠 <b>هوش مصنوعی جینکس</b>\n"
        f"{LINE}\n\n"
        f"🧩 مغز داخلی (بدون کلید): {on_off('brain_on')}\n"
        "▫️ بدون هیچ کلیدی کار می‌کند؛ خطاهای Railway، GitHub، پنل و کانفیگ را از روی متن تشخیص می‌دهد و راه‌حل قدم‌به‌قدم می‌دهد.\n\n"
        f"☁️ هوش مصنوعی ابری: {status}\n"
        "▫️ اختیاری؛ با کلید، مثل ChatGPT گفتگو می‌کند و اسکرین‌شات هم می‌خواند.\n\n"
        f"🏢 سرویس: <b>{html.escape(preset)}</b>\n"
        f"🤖 مدل: <code>{html.escape(c['model'] or '-')}</code>\n"
        f"🔑 کلید: <code>{html.escape(masked)}</code>\n\n"
        "در گروه چه کار می‌کند؟\n"
        "▫️ مثل یک متخصص جواب سؤال‌های پنل، Railway، GitHub و کانفیگ را می‌دهد\n"
        "▫️ متن خطا یا <b>اسکرین‌شات</b> را می‌خواند و می‌گوید کجا را اشتباه زده‌اند\n"
        "▫️ لینک‌های رسمی را با دکمه می‌فرستد\n"
        "▫️ پیام‌های مشکوک را تشخیص می‌دهد و پاک می‌کند\n\n"
        "💡 پیشنهاد: <b>Gemini</b> (رایگان) یا <b>AvalAI</b> (پرداخت ریالی)"
    )
    markup = kb([
        [tog("🧩 مغز داخلی", "brain_on", "a:t:brain_on")],
        [tog("☁️ هوش مصنوعی ابری", "ai_on", "a:t:ai_on")],
        [B("🏢 انتخاب سرویس", cb="a:ai_pre"), B("🔑 ثبت کلید API", cb="a:ai_key")],
        [B("🤖 انتخاب مدل", cb="a:ai_models"), B("✍️ نوشتن اسم مدل", cb="a:ai_model")],
        [B("📚 دانش اضافه", cb="a:ai_know"), B("🧪 تست", cb="a:ai_test")],
        [tog("🖼 خواندن اسکرین‌شات", "ai_vision", "a:t:ai_vision")],
        [tog("💬 جواب به همه پیام‌های مرتبط", "ai_all", "a:t:ai_all")],
        back(),
    ])
    return text, markup


@router.callback_query(F.data == "a:ai")
async def cb_ai(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await show(cb, *ai_view())


@router.callback_query(F.data == "a:ai_pre")
async def cb_ai_pre(cb: CallbackQuery):
    rows = [[B(v[0], cb=f"a:ai_set:{k}")] for k, v in ai.PRESETS.items()]
    rows.append([B("🔧 آدرس دلخواه (سازگار با OpenAI)", cb="a:ai_base")])
    rows.append(back("a:ai"))
    await show(
        cb,
        "🏢 <b>انتخاب سرویس هوش مصنوعی</b>\n"
        f"{LINE}\n\n"
        "🆓 <b>Gemini</b>: کلید رایگان از aistudio.google.com (سرور ربات باید خارج باشد)\n"
        "🇮🇷 <b>AvalAI</b>: پرداخت ریالی، از avalai.ir\n"
        "🌐 <b>OpenRouter</b>: صدها مدل با یک کلید\n"
        "⚡️ <b>Groq</b>: خیلی سریع",
        kb(rows),
    )


@router.callback_query(F.data.startswith("a:ai_set:"))
async def cb_ai_set(cb: CallbackQuery):
    k = cb.data.split(":")[2]
    if k in ai.PRESETS:
        _, base, model = ai.PRESETS[k]
        db.set_setting("ai_base", base)
        db.set_setting("ai_model", model)
    await show(cb, *ai_view())


@router.callback_query(F.data.in_({"a:ai_key", "a:ai_base", "a:ai_model", "a:ai_know", "a:ai_test"}))
async def cb_ai_ask(cb: CallbackQuery, state: FSMContext):
    what = cb.data.split(":")[1]
    prompts = {
        "ai_key": (SG.ai_key, "🔑 کلید API را بفرستید.\n🔒 پیام شما بلافاصله پاک می‌شود."),
        "ai_base": (SG.ai_base, "🔧 آدرس API را بفرستید (مثل <code>https://api.example.com/v1</code>)."),
        "ai_model": (SG.ai_model, "🤖 اسم دقیق مدل را بفرستید (مثل <code>gemini-flash-latest</code>)."),
        "ai_know": (SG.ai_know, "📚 <b>دانش اضافه</b>\nهر چیزی که می‌خواهید ربات بداند را بنویسید؛ مثلاً امکانات Super JinX، "
                                 "قوانین گروه، نکات نصب.\n\n<b>متن فعلی:</b>\n" +
                    html.escape((db.get_setting("ai_knowledge") or "خالی")[:3000])),
        "ai_test": (SG.ai_test, "🧪 یک سؤال بفرستید تا جواب هوش مصنوعی را ببینید.\nمثال: <i>ریلوی ارور 502 میده چیکار کنم؟</i>"),
    }
    st, text = prompts[what]
    await state.set_state(st)
    await cb.message.answer(text + "\n\n❎ لغو: /cancel")
    await cb.answer()


@router.message(StateFilter(SG.ai_key), F.text)
async def ai_key_save(msg: Message, state: FSMContext):
    db.set_setting("ai_key", msg.text.strip())
    try:
        await msg.delete()
    except Exception:
        pass
    await state.clear()
    await msg.answer("✅ کلید ذخیره شد.")
    await show(msg, *ai_view())


@router.message(StateFilter(SG.ai_base), F.text)
async def ai_base_save(msg: Message, state: FSMContext):
    db.set_setting("ai_base", msg.text.strip().rstrip("/"))
    await state.clear()
    await show(msg, *ai_view())


@router.message(StateFilter(SG.ai_model), F.text)
async def ai_model_save(msg: Message, state: FSMContext):
    db.set_setting("ai_model", msg.text.strip())
    await state.clear()
    await show(msg, *ai_view())


@router.message(StateFilter(SG.ai_know), F.text)
async def ai_know_save(msg: Message, state: FSMContext):
    db.set_setting("ai_knowledge", msg.text.strip()[:6000])
    await state.clear()
    await msg.answer("✅ دانش اضافه ذخیره شد.")
    await show(msg, *ai_view())


@router.message(StateFilter(SG.ai_test), F.text)
async def ai_test_run(msg: Message, state: FSMContext):
    await state.clear()
    c = ai.cfg()
    if not (c["base"] and c["key"] and c["model"]):
        await msg.answer("⚠️ اول سرویس، کلید و مدل را تنظیم کنید.")
        return
    wait = await msg.answer("⏳ در حال فکر کردن...")
    t0 = time.time()
    try:
        out = await ai.answer(msg.chat.id, msg.from_user.id, msg.from_user.first_name or "ادمین", msg.text)
        ai.forget(msg.chat.id, msg.from_user.id)
        body, _ = ai.render(out)
        footer = f"\n\n{LINE}\n⚡️ زمان پاسخ: {time.time() - t0:.1f} ثانیه"
        try:
            await wait.edit_text(body + footer, reply_markup=kb([back("a:ai")]))
        except Exception:
            await wait.edit_text(ai.TAG_RE.sub("", out)[:3800] + footer, reply_markup=kb([back("a:ai")]), parse_mode=None)
    except Exception as e:
        await wait.edit_text(f"❌ <b>خطا</b>\n<code>{html.escape(str(e))[:500]}</code>\n\n"
                             "کلید، آدرس سرویس و اسم مدل را چک کنید.", reply_markup=kb([back("a:ai")]))


@router.callback_query(F.data == "a:ai_models")
async def cb_ai_models(cb: CallbackQuery):
    c = ai.cfg()
    if not (c["base"] and c["key"]):
        await cb.answer("⚠️ اول سرویس و کلید را تنظیم کنید.", show_alert=True)
        return
    await cb.answer("⏳ گرفتن لیست مدل‌ها...")
    try:
        models = await ai.list_models()
    except Exception as e:
        await cb.message.answer(f"❌ لیست مدل‌ها گرفته نشد:\n<code>{html.escape(str(e))[:300]}</code>")
        return
    if not models:
        await cb.message.answer("⚠️ مدلی پیدا نشد؛ اسم مدل را دستی بنویسید.")
        return
    rows = chunk([B(m[:40], cb=f"a:ai_m:{i}") for i, m in enumerate(models)], 2)
    rows.append(back("a:ai"))
    db.set_setting("_models", "\n".join(models))
    await cb.message.answer("🤖 <b>یک مدل انتخاب کنید</b>\n💡 مدل‌های flash و mini سریع و ارزان‌اند.", reply_markup=kb(rows))


@router.callback_query(F.data.startswith("a:ai_m:"))
async def cb_ai_pick(cb: CallbackQuery):
    models = (db.get_setting("_models") or "").split("\n")
    i = int(cb.data.split(":")[2])
    if i < len(models):
        db.set_setting("ai_model", models[i])
    await show(cb, *ai_view())


# ================================================================ مشخصات ربات
class IdSG(StatesGroup):
    brand = State()
    channel = State()


def id_view():
    ch = db.get_setting("channel") or "❌ ثبت نشده"
    text = (
        "🏷 <b>مشخصات ربات</b>\n"
        f"{LINE}\n\n"
        f"💎 برند: <b>{html.escape(utils.brand())}</b>\n"
        f"📢 کانال: {html.escape(ch)}\n"
        f"💬 پشتیبانی: {support()}\n"
        f"🤖 ربات: @{utils.BOT_USERNAME}\n\n"
        "این مشخصات در خوش‌آمد، پیوی، دکمه‌ها و پروفایل ربات نمایش داده می‌شود.\n"
        "🛡 یوزرنیم ربات، پشتیبانی و کانال در برابر جعل هویت محافظت می‌شوند."
    )
    markup = kb([
        [B("💎 تغییر اسم برند", cb="a:id_brand"), B("📢 کانال ما", cb="a:id_channel")],
        [B("✨ اعمال روی پروفایل ربات", cb="a:id_apply")],
        [tog("🙋 کمک به کاربران در پیوی", "pv_help", "a:t:pv_help")],
        back(),
    ])
    return text, markup


@router.callback_query(F.data == "a:id")
async def cb_id(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await show(cb, *id_view())


@router.callback_query(F.data.in_({"a:id_brand", "a:id_channel"}))
async def cb_id_ask(cb: CallbackQuery, state: FSMContext):
    if cb.data == "a:id_brand":
        await state.set_state(IdSG.brand)
        await cb.message.answer("💎 اسم برند را بفرستید (مثل <code>Super JinX</code>).\n❎ لغو: /cancel")
    else:
        await state.set_state(IdSG.channel)
        await cb.message.answer("📢 یوزرنیم یا لینک کانال را بفرستید (مثل <code>@SuperJinx</code>).\n"
                                "برای حذف: <code>-</code>\n❎ لغو: /cancel")
    await cb.answer()


@router.message(StateFilter(IdSG.brand), F.text)
async def id_brand(msg: Message, state: FSMContext):
    db.set_setting("brand", msg.text.strip()[:40])
    await state.clear()
    await show(msg, *id_view())


@router.message(StateFilter(IdSG.channel), F.text)
async def id_channel(msg: Message, state: FSMContext):
    t = msg.text.strip().split()[0]
    if t == "-":
        t = ""
    elif "t.me/" in t:
        t = "@" + t.rstrip("/").split("/")[-1]
    elif not t.startswith("@") and not t.startswith("http"):
        t = "@" + t
    db.set_setting("channel", t)
    await state.clear()
    await show(msg, *id_view())


async def apply_profile(bot: Bot):
    b = utils.brand()
    ch = db.get_setting("channel") or ""
    desc = (f"💎 دستیار هوشمند {b}\n\n"
            "🚂 راه‌اندازی پنل روی Railway\n🐙 رفع مشکلات GitHub\n🧬 کانفیگ و سابلینک\n🛡 مدیریت و امنیت گروه\n\n"
            f"💬 پشتیبانی: {support()}" + (f"\n📢 کانال: {ch}" if ch else ""))
    short = f"💎 دستیار هوشمند {b} | پشتیبانی: {support()}"
    await bot.set_my_description(description=desc[:512])
    await bot.set_my_short_description(short_description=short[:120])


@router.callback_query(F.data == "a:id_apply")
async def cb_id_apply(cb: CallbackQuery, bot: Bot):
    try:
        await apply_profile(bot)
        await cb.answer("✅ توضیحات پروفایل ربات به‌روز شد.", show_alert=True)
    except Exception:
        await cb.answer("⚠️ انجام نشد؛ چند دقیقه بعد دوباره امتحان کنید.", show_alert=True)


# ================================================================ دستورهای مدیریت
MOD_HELP = (
    "👮 <b>دستورهای مدیریت گروه</b>\n"
    f"{LINE}\n\n"
    "روی پیام کاربر <b>ریپلای</b> کنید، یا آیدی‌اش را بنویسید:\n\n"
    "🔇 <code>سکوت</code> همیشگی\n"
    "🔇 <code>سکوت 15</code> پانزده دقیقه\n"
    "🔇 <code>سکوت @user 2 ساعت</code>\n"
    "🔇 <code>سکوت 123456789 1 روز</code>\n"
    "🔊 <code>آزاد</code> یا <code>رفع سکوت</code>\n\n"
    "⛔️ <code>بن</code> یا <code>بنش کن</code> همیشگی\n"
    "⛔️ <code>بن 3 روز</code>\n"
    "♻️ <code>رفع بن</code>\n"
    "👢 <code>اخراج</code> (بیرون می‌کند ولی می‌تواند برگردد)\n"
    "🗑 <code>پاک</code> پیام ریپلای‌شده را حذف می‌کند\n"
    "🔒 <code>قفل گروه</code> / 🔓 <code>باز کردن گروه</code>\n\n"
    "⏱ واحدها: ثانیه، دقیقه، ساعت، روز، هفته. عدد تنها یعنی دقیقه.\n\n"
    "📲 <b>از همین پیوی</b> هم می‌شود (روی همه گروه‌ها اعمال می‌شود):\n"
    "<code>بن 123456789</code>   <code>سکوت @user 30</code>   <code>رفع بن 123456789</code>"
)


@router.callback_query(F.data == "a:modhelp")
async def cb_modhelp(cb: CallbackQuery):
    await show(cb, MOD_HELP, kb([back()]))


@router.message(StateFilter(None), F.text.func(lambda t: mod.detect(t) in ("mute", "unmute", "ban", "unban", "kick")))
async def pv_moderate(msg: Message, bot: Bot):
    cmd = mod.detect(msg.text)
    uid, who = await mod.resolve_target(msg, bot, use_reply=False)
    if uid is None:
        await msg.answer("⚠️ آیدی عددی یا @یوزرنیم کاربر را بنویسید، یا روی پیام فورواردی‌اش ریپلای کنید.\nمثال: <code>بن 123456789</code>")
        return
    if is_admin_id(uid):
        await msg.answer("🛡 این کاربر ادمین ربات است.")
        return
    sec = mod.parse_duration(re.sub(r"@\w+", " ", msg.text)) if cmd in ("mute", "ban") else None
    groups = db.list_groups()
    if not groups:
        await msg.answer("⚠️ ربات در هیچ گروهی نیست.")
        return
    ok = 0
    for g in groups:
        try:
            await mod.apply(bot, g["chat_id"], cmd, uid, sec)
            ok += 1
        except Exception:
            pass
    text, _ = mod.result_text(cmd, who, sec)
    await msg.answer(f"{text}\n\n👥 اعمال‌شده در <b>{ok}</b> از <b>{len(groups)}</b> گروه",
                     reply_markup=kb([back(text="🏠 پنل مدیریت")]))


# ================================================================ لینک‌های مهم
def links_view():
    links = db.list_links()
    text = (
        "🔗 <b>لینک‌های مهم</b>\n"
        f"{LINE}\n\n"
        "لینک‌هایی مثل ریپوی گیتهاب، کانال آموزش یا Railway را اینجا ثبت کنید.\n"
        "هر کس در گروه بگوید مثلاً «لینک گیتهاب رو بدید»، ربات فوراً با دکمه می‌فرستد. هوش مصنوعی هم فقط از همین لینک‌ها استفاده می‌کند.\n\n"
        + ("\n".join(f"{i}. {html.escape(l['title'])}\n    🔑 <i>{html.escape(l['keywords'])}</i>" for i, l in enumerate(links, 1))
           if links else "هنوز لینکی ثبت نشده.")
    )
    rows = [[B("➕ افزودن لینک", cb="a:link_add", style=GREEN)]]
    rows += [[B(f"🗑 {l['title']}", cb=f"a:link_del:{l['id']}", style=RED)] for l in links]
    rows.append(back())
    return text, kb(rows, rainbow=False)


@router.callback_query(F.data == "a:links")
async def cb_links(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await show(cb, *links_view())


@router.callback_query(F.data.startswith("a:link_del:"))
async def cb_link_del(cb: CallbackQuery):
    db.del_link(int(cb.data.split(":")[2]))
    await show(cb, *links_view())


@router.callback_query(F.data == "a:link_add")
async def cb_link_add(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SG.link_title)
    await show(cb, "1️⃣ عنوان دکمه را بفرستید.\nمثال: <code>🐙 گیتهاب Super JinX</code>\n\n❎ لغو: /cancel", kb([back("a:links")]))


@router.message(StateFilter(SG.link_title), F.text)
async def link_title(msg: Message, state: FSMContext):
    await state.update_data(l_title=msg.text.strip()[:60])
    await state.set_state(SG.link_url)
    await msg.answer("2️⃣ لینک را بفرستید (با https://).")


@router.message(StateFilter(SG.link_url), F.text)
async def link_url(msg: Message, state: FSMContext):
    url = msg.text.strip().split()[0]
    if not url.startswith(("http://", "https://", "tg://")):
        await msg.answer("⚠️ لینک باید با https:// شروع شود.")
        return
    await state.update_data(l_url=url)
    await state.set_state(SG.link_kw)
    await msg.answer("3️⃣ کلمات کلیدی را با کاما بفرستید.\nمثال: <code>گیتهاب,گیت هاب,github,ریپو,سورس</code>")


@router.message(StateFilter(SG.link_kw), F.text)
async def link_kw(msg: Message, state: FSMContext):
    d = await state.get_data()
    db.add_link(d["l_title"], msg.text.strip(), d["l_url"])
    await state.clear()
    await msg.answer("✅ لینک اضافه شد.")
    await show(msg, *links_view())


# ================================================================ راهنماها
def guides_view():
    rows = [[B("➕ افزودن راهنمای جدید", cb="a:g_add", style=GREEN)]]
    rows += chunk([B(g["title"], cb=f"a:g_view:{g['id']}") for g in db.list_guides()], 2)
    rows.append(back())
    return "📚 <b>راهنماها</b>\n" + LINE + "\n\nبرای ویرایش یا حذف روی هر راهنما بزنید.", kb(rows)


@router.callback_query(F.data == "a:guides")
async def cb_guides(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await show(cb, *guides_view())


@router.callback_query(F.data.startswith("a:g_view:"))
async def cb_g_view(cb: CallbackQuery):
    gid = int(cb.data.split(":")[2])
    g = db.get_guide(gid)
    if not g:
        await cb.answer("پیدا نشد", show_alert=True)
        return
    markup = kb([
        [B("✏️ عنوان", cb=f"a:g_ed:title:{gid}"), B("🔑 کلمات کلیدی", cb=f"a:g_ed:keywords:{gid}")],
        [B("📝 متن", cb=f"a:g_ed:body:{gid}"), B("🗑 حذف", cb=f"a:g_del:{gid}", style=RED)],
        back("a:guides"),
    ])
    text = f"{g['body']}\n\n{LINE}\n🔑 <b>کلمات کلیدی:</b> {html.escape(g['keywords'] or '')}"
    await show(cb, text[:4000], markup)


@router.callback_query(F.data.startswith("a:g_del:"))
async def cb_g_del(cb: CallbackQuery):
    db.del_guide(int(cb.data.split(":")[2]))
    await show(cb, *guides_view())


@router.callback_query(F.data.startswith("a:g_ed:"))
async def cb_g_edit(cb: CallbackQuery, state: FSMContext):
    _, _, field, gid = cb.data.split(":")
    await state.set_state(SG.g_edit)
    await state.update_data(field=field, gid=int(gid))
    names = {"title": "عنوان", "keywords": "کلمات کلیدی (با کاما جدا کنید)", "body": "متن راهنما"}
    await cb.message.answer(f"✍️ {names[field]} جدید را بفرستید.\n❎ لغو: /cancel")
    await cb.answer()


@router.message(StateFilter(SG.g_edit), F.text)
async def g_edit_save(msg: Message, state: FSMContext):
    data = await state.get_data()
    value = msg.html_text if data["field"] == "body" else msg.text.strip()
    db.update_guide(data["gid"], data["field"], value)
    await state.clear()
    await msg.answer("✅ انجام شد.")
    await show(msg, *guides_view())


@router.callback_query(F.data == "a:g_add")
async def cb_g_add(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SG.g_title)
    await show(cb, "1️⃣ عنوان راهنما را بفرستید (مثلاً: 🛰 نصب پنل مرزنشین).\n❎ لغو: /cancel", kb([back("a:guides")]))


@router.message(StateFilter(SG.g_title), F.text)
async def g_title(msg: Message, state: FSMContext):
    await state.update_data(title=msg.text.strip()[:60])
    await state.set_state(SG.g_keywords)
    await msg.answer(
        "2️⃣ کلمات کلیدی را با کاما جدا کنید.\n"
        "وقتی کسی در گروه سؤالی با این کلمات بپرسد، ربات همین راهنما را جواب می‌دهد.\n\n"
        "مثال: <code>مرزنشین,marzneshin</code>"
    )


@router.message(StateFilter(SG.g_keywords), F.text)
async def g_keywords(msg: Message, state: FSMContext):
    await state.update_data(keywords=msg.text.strip())
    await state.set_state(SG.g_body)
    await msg.answer("3️⃣ متن کامل راهنما را بفرستید. بولد، کد و ایموجی مجاز است.")


@router.message(StateFilter(SG.g_body), F.text)
async def g_body(msg: Message, state: FSMContext):
    data = await state.get_data()
    db.add_guide(data["title"], data["keywords"], msg.html_text)
    await state.clear()
    await msg.answer("✅ راهنما اضافه شد.")
    await show(msg, *guides_view())


def is_admin_id(uid: int) -> bool:
    return uid in ADMIN_IDS
