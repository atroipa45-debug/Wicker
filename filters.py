"""تشخیص لینک تبلیغاتی و فحش/تهدید. همه‌چیز در حافظه و سریع."""
import difflib
import re

import db

# ---------------------------------------------------------------- لینک
# کانفیگ‌ها مجازند؛ قبل از بررسی از متن حذف می‌شوند تا SNI یا مسیرشان اشتباهی لینک حساب نشود.
CONFIG_RE = re.compile(
    r"(?:vless|vmess|trojan|ssr?|hysteria2?|hy2|tuic|wireguard|wg|socks5?|juicity|anytls|naive\+https?|mieru)://\S+",
    re.I,
)
TG_RE = re.compile(
    r"(?<![A-Za-z0-9_\-])(?:https?://)?(?:www\.)?(?:t|telegram)\s*(?:\.|\[\.\]|\(\.\)|\[dot\]|\(dot\)|\sdot\s|نقطه)\s*(?:me|dog)\s*/\s*([^\s]*)",
    re.I,
)
TG_SCHEME_RE = re.compile(r"tg://(join|resolve)\?([^\s]*)", re.I)
OTHER_RE = re.compile(
    r"(?:chat\.whatsapp\.com|(?<![a-z])wa\.me/|whatsapp\.com/channel|eitaa\.com|rubika\.ir|(?<![a-z])ble\.ir|splus\.ir|"
    r"(?<![a-z])gap\.im|igap\.net|discord\.gg|discord(?:app)?\.com/invite|soroush-app\.ir)",
    re.I,
)
TG_ALLOWED_PATHS = {"proxy", "socks", "addstickers", "addemoji", "addtheme", "setlanguage", "share", "iv"}


def _allowed_set(own) -> set[str]:
    if not own:
        return set()
    if isinstance(own, str):
        own = [own]
    return {o.lower().lstrip("@") for o in own if o}


def _bad_tg_path(path: str, own_username) -> bool:
    path = path.strip().lstrip("/")
    if not path:
        return False
    first = re.split(r"[/?#]", path)[0]
    low = first.lower()
    if low in TG_ALLOWED_PATHS:
        return False
    if low.startswith("+") or low == "joinchat":
        return True
    if low.endswith("bot"):  # آیدی و لینک ربات مشکلی ندارد
        return False
    if low in _allowed_set(own_username):  # لینک خود گروه، پشتیبانی و کانال خودمان
        return False
    return True


def text_has_bad_link(text: str, own_username=None) -> bool:
    if not text:
        return False
    text = CONFIG_RE.sub(" ", text)
    if OTHER_RE.search(text):
        return True
    for m in TG_RE.finditer(text):
        if _bad_tg_path(m.group(1), own_username):
            return True
    for m in TG_SCHEME_RE.finditer(text):
        kind, query = m.group(1).lower(), m.group(2)
        if kind == "join":
            return True
        dom = re.search(r"domain=([A-Za-z0-9_]+)", query)
        if dom and not dom.group(1).lower().endswith("bot") and dom.group(1).lower() not in _allowed_set(own_username):
            return True
    return False


def message_has_bad_link(msg, own_username=None) -> bool:
    text = msg.text or msg.caption or ""
    parts = [text]
    for e in (msg.entities or msg.caption_entities or []):
        if getattr(e, "url", None):
            parts.append(e.url)
    if msg.reply_markup and getattr(msg.reply_markup, "inline_keyboard", None):
        for row in msg.reply_markup.inline_keyboard:
            for b in row:
                if b.url:
                    parts.append(b.url)
    return any(text_has_bad_link(p, own_username) for p in parts)


# ---------------------------------------------------------------- فحش و تهدید
_FA = str.maketrans({
    "ي": "ی", "ك": "ک", "ة": "ه", "ۀ": "ه", "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ؤ": "و", "ئ": "ی",
    "\u200c": "", "\u200d": "", "\u200e": "", "\u200f": "", "ـ": "", "_": "",
    "0": "o", "@": "a", "$": "s",
})
_DIAC = re.compile(r"[\u064B-\u065F\u0670]")
_NONW = re.compile(r"[^\w\s]")


def _base(t: str) -> str:
    t = _DIAC.sub("", (t or "").lower().translate(_FA))
    t = _NONW.sub("", t)
    toks = t.split()
    # «ک ی ر» با فاصله بین حروف را هم سرهم می‌کند
    out, run = [], []
    for tok in toks:
        if len(tok) == 1:
            run.append(tok)
            continue
        if len(run) >= 3:
            out.append("".join(run))
        else:
            out.extend(run)
        run = []
        out.append(tok)
    out.extend(["".join(run)] if len(run) >= 3 else run)
    return " ".join(out)


def _c3(t):  # «کیییییر» → «کیر»
    return re.sub(r"(.)\1{2,}", r"\1", t)


def _c2(t):  # «کییر» → «کیر»
    return re.sub(r"(.)\1+", r"\1", t)


# داخل هر کلمه پیدا شود
CONTAINS = """
کسکش کصکش کسخل کصخل کسشر کصشر کسشعر کصشعر کسننت کصننت کسمادر کصمادر کسخوار کصخوار کسخار
خارکس خوارکس خارکص خوارکص کسده کصده کیرم کیرت کیرخر کیرتو کیرمو کیرشو کیرمون
جنده جندس مادرجنده مادرقحبه قحبه حرومزاده حرامزاده حرومی بیناموس ناموستو ناموسشو جاکش
دیوث پفیوز گاییدم گاییدمت گاییدی گاییده گاییدن میگامت بگامت میگامتون کونکش کونده کونی کونتو
پدرسگ سگپدر تخمسگ گوهخور گهخور گوهخوری بیشرف بیپدر پتیاره فاحشه هرزه ننتو ننهت
بیشعور عوضی کثافت حیوون
fuck motherfucker bitch koskesh kosnanat madarjende jende kirkhar kharkose kharkosde
binamoos bisharaf pedarsag haromzade gaidam gayidam kooni jakesh
""".split()

# فقط کلمه کامل (چون داخل کلمه‌های عادی هم پیدا می‌شوند)
EXACT = """
کیر کص کون ننت کونت احمق احمقی الاغ لاشی لاشیه اسکل اسکلی
میکشمت میکشمتون بکشمت بکشمتون میزنمت بزنمت میکشیمت
kir kos kiri koni shit dick pussy asshole lashi
""".split()

# عبارت چندکلمه‌ای
PHRASES = [
    "کس ننت", "کس مادرت", "کس خل", "کس شعر", "کس نگو", "کس کش", "کیر خر", "تو کونت", "مادر جنده",
    "خونتو پیدا", "ادرستو پیدا", "ادرس خونتو", "میام سراغت", "میایم سراغت", "حسابتو میرسم",
    "حالتو میگیرم", "هکت میکنم", "هکت میکنیم", "اکانتتو هک", "گوشیتو هک", "ابروتو میبرم", "ابروتو ببرم",
    "عکساتو پخش", "اطلاعاتتو پخش", "سرتو میبرم", "لهت میکنم", "داغونت میکنم", "پدرتو در میارم",
    "پدرتو درمیارم", "خفت میکنم", "نابودت میکنم", "بیچارت میکنم", "زندت نمیذارم", "زنده نمیذارمت",
    "تیکه تیکت", "جرت میدم", "میفرستمت اون دنیا", "ترورت میکنم", "دودمانتو",
    "kos nanat", "kir khar", "madar jende",
]


def _prep(words):
    return [(w, _c2(w)) for w in (_base(x) for x in words) if w]


_C = _prep(CONTAINS)
_E = {w for w, _ in _prep(EXACT)} | {c for _, c in _prep(EXACT)}
_P = _prep(PHRASES)


def has_bad_word(text: str) -> bool:
    if not text:
        return False
    base = _base(text)
    v3, v2 = _c3(base), _c2(base)
    padded3, padded2 = f" {v3} ", f" {v2} "
    toks = set(v3.split()) | set(v2.split())
    if toks & _E:
        return True
    for w, c in _C:
        if w in v3 or c in v2:
            return True
    for w, c in _P:
        if f" {w} " in padded3 or f" {c} " in padded2 or w.replace(" ", "") in v3.replace(" ", ""):
            return True
    for raw in db.list_badwords():
        w = _base(raw)
        if not w:
            continue
        if " " in w:
            if f" {w} " in padded3:
                return True
        elif len(w) <= 3:
            if w in toks or _c2(w) in toks:
                return True
        elif w in v3 or _c2(w) in v2:
            return True
    return False


# ---------------------------------------------------------------- خرید
BUY_HINTS = [
    "خرید", "بخرم", "میخرم", "میخوام بخرم", "قیمت", "چنده", "چند میدی", "چند میدین", "میفروشی", "میفروشید",
    "فروش", "کانفیگ میخوام", "کانفیگ میخام", "پنل میخوام", "پنل میخام", "سرویس میخوام", "سرویس میخام",
    "اشتراک میخوام", "تمدید", "کانفیگ دارید", "کانفیگ داری", "پنل دارید", "پنل داری", "فیلترشکن میخوام",
    "vpn میخوام", "کانفیگ بدید", "کانفیگ بده", "پنل بدید", "پنل بده",
]
_BUY = [_base(x) for x in BUY_HINTS]


_HELP_INTENT = re.compile(r"(?:نصب|راه ?اندازی|بسازم|بسازیم|اموزش|ارور|خطا|مشکل|دیپلوی|deploy|ریلوی|railway|گیتهاب|github|چطور|چجوری|چطوری)")


def wants_to_buy(text: str) -> bool:
    t = f" {_base(text)} "
    if _HELP_INTENT.search(t):
        return False
    return any(h in t for h in _BUY)


# ---------------------------------------------------------------- دعوت به پیوی و بیو
PV_WORDS = r"(?:پیوی|پی وی|پیویی|پیوی م|پیویم|پیوم|پی ویم|pv|p v|pvm|pm|دایرکت|دایرکتم|direct|dm|خصوصی|خصوصیم|private)"
INVITE = (
    r"(?:بیا|بیاید|بیاین|بیاد|بیان|بیای|بیایید|بده|بدید|بدین|بدی|پیام|پی ام|مسیج|مسج|msg|message|massage|بزن|بزنید|"
    r"بزنین|منتظرم|هستم|بفرست|بفرستید|bia|biya|bede|bedid|send|text|چک|سر بزن|اد کن|ادد|add|کار دارم|کارت دارم|دارم|داریم|موجوده|هست)"
)
_PV1 = re.compile(rf"(?:^|\s){PV_WORDS}(?:\s+\S+){{0,3}}\s+{INVITE}", re.I)
_PV2 = re.compile(rf"(?:^|\s){INVITE}(?:\s+\S+){{0,3}}\s+{PV_WORDS}(?:\s|$)", re.I)
_PV_SHORT = re.compile(rf"^(?:\S+\s+){{0,2}}{PV_WORDS}(?:\s+\S+){{0,1}}$", re.I)
_BIO = re.compile(
    r"(?:بیوم|بیومو|بیوگرافیم|بیو من|بیوی من|تو بیو|توی بیو|داخل بیو|تو بیوم|بیو رو|بیو را|بیوو|"
    r"bio|biom|bioam|پروفایلم|پروفایلمو|پروفمو|پروفم|تو پروفایل|توی پروفایل|عکس پروفایلم|اسممو|تو اسمم|"
    r"کانالم|کانال من|گروهم|گروه من|چنلم|لینک تو بیو|ایدیمو|ایدی منو|ایدیم رو)",
    re.I,
)
_BIO_ONLY = re.compile(r"(?:^|\s)بیو(?:\s|$)")
_BIO_VERB = re.compile(r"(?:چک|ببین|ببینید|نگاه|بخون|سر بزن|check|bebin|عضو|جوین|join)", re.I)


def is_pv_spam(text: str, allow: tuple[str, ...] = ()) -> bool:
    if not text:
        return False
    low = text.lower()
    if any(a and a.lower() in low for a in allow):
        return False
    t = _c2(_base(text))
    if re.search(r"(?:^|\s)(?:ربات|پشتیبانی)(?:\s|$)", t):
        return False
    if _PV1.search(t) or _PV2.search(t) or _PV_SHORT.search(t):
        return True
    if _BIO.search(t) and (_BIO_VERB.search(t) or len(t.split()) <= 6):
        return True
    if _BIO_ONLY.search(t) and _BIO_VERB.search(t):
        return True
    return False


# نشانه‌های مشکوک: فقط این پیام‌ها برای بررسی به هوش مصنوعی فرستاده می‌شوند (سریع و کم‌هزینه)
_SOFT = re.compile(
    r"(?:pv|پیو|پی و|بیو|bio|دایرکت|خصوص|direct|تبلیغ|ارزون|ارزان|تخفیف|میفروشم|میفروشیم|عضو شو|جوین|join|ممبر|member|"
    r"کانالم|چنلم|گروهم|ادد|پیام بد|مسیج بد|ایدیم|پروفایل|پروفم|تومن|تومان|حراج|سکه|ترید|سیگنال|بکشم|میکشم|میزنمت|پیدات|سراغت|"
    r"لعنت|خفه|گمشو|بیشعور|مادر|ننه|خوارو|خواهر)",
    re.I,
)


def suspicious(text: str) -> bool:
    return bool(text) and bool(_SOFT.search(_base(text)))


# ---------------------------------------------------------------- تبلیغات
_STRONG = re.compile(
    r"(?:میفروشم|میفروشیم|بفروشم|فروش (?:ویژه|کانفیگ|پنل|ممبر|اکانت|سرویس|vpn|فیلترشکن)|فروشی|نمایندگی میدیم|نمایندگی فعال|"
    r"تست رایگان|قیمت ویژه|حراج|ممبر|فالوور|فالور|follower|ممبر فیک|ممبر واقعی|سین پست|ری اکشن|ریاکشن|نامبر مجازی|شماره مجازی|"
    r"کسب درامد|کسب درآمد|سرمایه گذاری|سیگنال|فارکس|کازینو|casino|بونوس|bonus|airdrop|ایردراپ|پیش بینی فوتبال|"
    r"خرید از ما|از ما بخرید|سفارش بدید|سفارش دهید|ثبت سفارش)",
    re.I,
)
_SALE = re.compile(
    r"(?:فروش|ارزون|ارزان|تخفیف|نمایندگی|عمده|سفارش|پکیج|تعرفه|تومن|تومان|هزارتومن|ریال|به قیمت|با قیمت|"
    r"لایک|ویو|استارز|stars|پریمیوم|premium|درامد|ترید|ارز دیجیتال|رایگان)",
    re.I,
)
_OFFER = re.compile(r"(?:دارم|داریم|موجوده|موجود است|ارائه میدیم|ارائه میدهیم|میدم|میدیم|بدم|بدیم|هست)", re.I)
_COME = re.compile(r"(?:^|\s)(?:بیا|بیاین|بیاید|بیایید|برید|بزنید|بزن|ببینید|چک کنید)(?:\s|$)")
_JOIN = re.compile(r"(?:عضو شو|عضو شید|عضو بشید|جوین شو|جوین شید|جوین بدید|بپیوندید|بیاید کانال|بیاین کانال|کانال ما|"
                   r"گروه ما|چنل ما|فالو کنید|follow|join|سابسکرایب|subscribe|سر بزنید|ادد شید|اد شید)", re.I)
_PRICE = re.compile(r"\d+\s*(?:k|ک|هزار|تومن|تومان|ت|میلیون|t)\b", re.I)
_PHONE = re.compile(r"(?:\+98|0098|۰۰۹۸|\b0|۰)\s*9[\d۰-۹]{2}[\s\-]?[\d۰-۹]{3}[\s\-]?[\d۰-۹]{4}")
_MENTION = re.compile(r"@([A-Za-z][A-Za-z0-9_]{3,31})")
_FA_DIG = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def is_ad(text: str, allow_users: tuple[str, ...] = ()) -> bool:
    if not text:
        return False
    raw = text.translate(_FA_DIG)
    if _PHONE.search(raw):
        return True
    t = _c3(_base(raw))
    allow = {a.lower().lstrip("@") for a in allow_users if a}
    foreign = [m for m in _MENTION.findall(raw) if m.lower() not in allow and not m.lower().endswith("bot")]
    if _STRONG.search(t):
        return True
    sale = bool(_SALE.search(t))
    offer = bool(_OFFER.search(t))
    join = bool(_JOIN.search(t))
    price = bool(_PRICE.search(raw))
    score = (2 if sale and (offer or price) else 1 if sale else 0) + (1 if price else 0) + (2 if join else 0)
    if foreign:
        score += 1
        if sale or join or _COME.search(t):
            score += 2
    return score >= 3


# ---------------------------------------------------------------- جعل هویت
def _compact(s: str) -> str:
    return re.sub(r"[^a-z0-9\u0600-\u06ff]", "", (s or "").lower().translate(_FA))


_STAFF = re.compile(r"(?:support|admin|ادمین|پشتیبان|مدیر|official|رسمی|owner|مالک|bot|ربات)", re.I)


def is_impersonator(user, protected_usernames: list[str], brand_names: list[str]) -> bool:
    """کاربری که اسم یا یوزرنیمش شبیه ربات، پشتیبانی یا برند ماست."""
    uname = (user.username or "").lower()
    prot = [p.lower().lstrip("@") for p in protected_usernames if p]
    if uname and uname in prot:
        return False
    cu = _compact(uname)
    for p in prot:
        cp = _compact(p)
        if cu and cp and (difflib.SequenceMatcher(None, cu, cp).ratio() >= 0.8 or (len(cp) >= 6 and cp in cu)):
            return True
    name = _compact(user.full_name or "")
    for b in brand_names:
        cb = _compact(b)
        if len(cb) >= 4 and (cb in name or cb in cu) and (_STAFF.search(user.full_name or "") or _STAFF.search(uname)):
            return True
    return False


# ---------------------------------------------------------------- زمان (برای سکوت و بن)
_NUM_WORDS = {
    "نیم": 0.5, "یک": 1, "یه": 1, "دو": 2, "سه": 3, "چهار": 4, "پنج": 5, "شش": 6, "شیش": 6, "هفت": 7, "هشت": 8,
    "نه": 9, "ده": 10, "یازده": 11, "دوازده": 12, "پانزده": 15, "پونزده": 15, "بیست": 20, "سی": 30, "چهل": 40,
    "چهل و پنج": 45, "پنجاه": 50, "شصت": 60, "نود": 90, "صد": 100,
}
_UNITS = [
    (r"(?:ثانیه|sec|s\b)", 1),
    (r"(?:دقیقه|دقه|min|m\b|دقيقه)", 60),
    (r"(?:ساعت|hour|h\b)", 3600),
    (r"(?:روز|day|d\b)", 86400),
    (r"(?:هفته|week|w\b)", 604800),
    (r"(?:ماه|month)", 2592000),
]


def parse_duration(text: str) -> int | None:
    """«۱۵ دقیقه» ← 900 ثانیه. عدد تنها یعنی دقیقه. اگر زمانی نبود None."""
    t = (text or "").translate(_FA_DIG).lower()
    t = re.sub(r"@\w+|\b\d{6,}\b", " ", t)  # آیدی‌ها عدد زمان حساب نشوند
    m = re.search(r"(\d+(?:\.\d+)?)\s*([^\d\s]*)", t)
    num, rest = None, ""
    if m:
        num, rest = float(m.group(1)), t[m.end(1):]
    else:
        for w, v in sorted(_NUM_WORDS.items(), key=lambda x: -len(x[0])):
            mm = re.search(rf"(?:^|\s){w}(?:\s|$)", t)
            if mm:
                num, rest = v, t[mm.end():]
                break
    if num is None:
        return None
    rest = rest.strip()[:12]
    for pat, mult in _UNITS:
        if re.match(pat, rest):
            return int(num * mult)
    return int(num * 60)


def human_duration(sec: int | None) -> str:
    from sub import fa
    if not sec:
        return "همیشگی"
    for size, name in ((604800, "هفته"), (86400, "روز"), (3600, "ساعت"), (60, "دقیقه")):
        if sec >= size and sec % size == 0:
            return f"{fa(sec // size)} {name}"
    if sec >= 60:
        return f"{fa(round(sec / 60))} دقیقه"
    return f"{fa(sec)} ثانیه"
