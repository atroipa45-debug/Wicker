"""مغز داخلی ربات (بدون نیاز به کلید API).
خطاها را از روی متن پیام یا لاگ تشخیص می‌دهد و دقیق می‌گوید کجا را اشتباه زده‌اند و چه کار کنند.
اگر کلید هوش مصنوعی ابری ثبت شود، آن هم کنار همین مغز کار می‌کند."""
import difflib
import random
import re

import db

_FIX = str.maketrans({"ي": "ی", "ك": "ک", "\u200c": " ", "ة": "ه", "آ": "ا", "أ": "ا", "إ": "ا"})


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").translate(_FIX).lower()).strip()


# ---------------------------------------------------------------- پایگاه تشخیص خطا
# (الگوها، عنوان تشخیص، راه‌حل)  ترتیب مهم است: خطاهای دقیق‌تر بالاترند.
RW = r"(?:railway|ریلوی|رلوی|ریل وی|رل وی|ریلوای)"
DIAG = [
    (
        [r"exec format error", r"bad interpreter", r"\\r", r"/entrypoint\.sh.*(?:no such file|not found)",
         r"no such file or directory.*\.sh", r"exec /\S+\.sh"],
        "فایل‌ها با گوشی یا ویندوز ادیت شده‌اند و خط‌بندی خراب شده (CRLF).",
        "1️⃣ داخل <code>Dockerfile</code> قبل از خط <code>ENTRYPOINT</code> این را بگذار:\n"
        "<code>RUN sed -i 's/\\r$//' /entrypoint.sh &amp;&amp; chmod +x /entrypoint.sh</code>\n"
        "2️⃣ کامیت کن تا Railway دوباره دیپلوی کند.\n"
        "💡 فایل‌های Super JinX این خط را از قبل دارند؛ اگر نداری، فایل‌ها را از نسخه اصلی دوباره آپلود کن.",
    ),
    (
        [r"permission denied"],
        "فایل اجرایی دسترسی اجرا ندارد.",
        "1️⃣ در <code>Dockerfile</code> اضافه کن:\n<code>RUN chmod +x /entrypoint.sh</code>\n"
        "2️⃣ کامیت کن و صبر کن دیپلوی تمام شود.",
    ),
    (
        [r"dockerfile.*(?:not found|does not exist|couldn'?t|could not)", r"no dockerfile", r"failed to read dockerfile",
         r"nixpacks", r"railpack", r"could not determine how to build", r"no start command"],
        "Railway فایل <code>Dockerfile</code> را پیدا نکرده؛ فایل‌ها در ریشه ریپو نیستند یا زیپ را اکسترکت نکرده‌ای.",
        "1️⃣ در GitHub ببین <code>Dockerfile</code> دقیقاً در صفحه اول ریپو باشد، نه داخل پوشه.\n"
        "2️⃣ اگر داخل پوشه است: Railway ← سرویس ← Settings ← <b>Root Directory</b> را اسم همان پوشه بگذار.\n"
        "3️⃣ اسم فایل باید دقیقاً <code>Dockerfile</code> باشد (D بزرگ، بدون پسوند).\n"
        "4️⃣ خود فایل زیپ را آپلود نکن؛ اول اکسترکت کن.",
    ),
    (
        [r"application failed to respond", r"\b502\b", r"bad gateway", r"\b503\b", r"service unavailable",
         r"target port", r"ریکوئست.*نمیرسه", r"سایت.*(?:باز نمیشه|بالا نمیاد|لود نمیشه)", r"دامنه.*(?:باز نمیشه|کار نمیکنه)"],
        "پورت دامنه با پورت برنامه یکی نیست، یا برنامه هنوز کامل بالا نیامده.",
        "1️⃣ Railway ← سرویس ← Settings ← <b>Networking</b>\n"
        "2️⃣ روی دامنه بزن و <b>Target Port</b> را بگذار <code>8080</code> (برای Super JinX).\n"
        "3️⃣ ۲ تا ۳ دقیقه صبر کن و صفحه را رفرش کن.\n"
        "4️⃣ اگر باز هم نشد، Deploy Logs را ببین که خطای قرمز ندارد.",
    ),
    (
        [r"health ?check", r"هلث ?چک", r"healthz"],
        "هلث‌چک رد شده؛ معمولاً مسیر یا پورت اشتباه است یا برنامه دیر بالا می‌آید.",
        "1️⃣ در <code>railway.json</code> مسیر <code>healthcheckPath</code> باید <code>/healthz</code> باشد.\n"
        "2️⃣ <code>healthcheckTimeout</code> را روی <code>300</code> بگذار.\n"
        "3️⃣ Target Port دامنه را <code>8080</code> بگذار.\n"
        "4️⃣ دوباره Redeploy کن.",
    ),
    (
        [r"out of memory", r"\boom\b", r"killed", r"memory limit", r"exit code 137"],
        "رم سرویس تمام شده.",
        "1️⃣ Railway ← سرویس ← Settings ← <b>Resource Limits</b> را چک کن.\n"
        "2️⃣ اگر روی Trial هستی، رم محدود است؛ پلن Hobby رم بیشتری می‌دهد.\n"
        "3️⃣ تعداد کاربر و اینباندهای اضافه را کم کن.",
    ),
    (
        [r"trial", r"limited", r"usage limit", r"insufficient", r"not enough credit", r"out of credit", r"credit",
         r"اعتبار.*(?:تموم|تمام)", r"پلن", r"hobby", r"verify.*account", r"account.*(?:verify|verification)"],
        "اعتبار یا محدودیت اکانت Railway.",
        "1️⃣ Railway ← آیکون پروفایل ← <b>Usage</b> را ببین چقدر اعتبار مانده.\n"
        "2️⃣ اکانت Limited Trial باید با اکانت GitHub قدیمی‌تر تأیید شود یا پلن <b>Hobby</b> فعال شود.\n"
        "3️⃣ بعد از شارژ، روی سرویس <b>Redeploy</b> بزن.",
    ),
    (
        [r"repo(?:sitory)?.*(?:not found|نمیاد|نیست|پیدا نمیشه|نمیبینم|نشون نمیده)", r"no repositories",
         r"configure github app", r"ریپو.*(?:نمیاد|نیست|پیدا نمیشه)"],
        "Railway به ریپوی GitHub دسترسی ندارد.",
        "1️⃣ در Railway موقع Deploy from GitHub، گزینه <b>Configure GitHub App</b> را بزن.\n"
        "2️⃣ در صفحه GitHub، گزینه <b>All repositories</b> یا اسم همان ریپو را انتخاب کن و Save بزن.\n"
        "3️⃣ برگرد Railway و صفحه را رفرش کن.",
    ),
    (
        [r"اطلاعات.*(?:پاک|پرید|رفت)", r"(?:یوزر|کاربر)ها.*(?:پاک|پرید|رفت)", r"بعد (?:از )?(?:ردیپلوی|ری ?استارت|اپدیت).*(?:پاک|ریست)",
         r"\bvolume\b", r"ولوم", r"data lost", r"ریست شد"],
        "Volume نساخته‌ای؛ برای همین با هر دیپلوی اطلاعات پاک می‌شود.",
        "1️⃣ Railway ← روی سرویس راست‌کلیک یا ⌘K ← <b>Add Volume</b>\n"
        "2️⃣ Mount Path: <code>/var/lib/pasarguard</code> (برای Super JinX)\n"
        "3️⃣ یک بار Redeploy کن. از این به بعد اطلاعات می‌ماند.",
    ),
    (
        [r"(?:رمز|پسورد|password|یوزرنیم|username|لاگین|login).*(?:اشتباه|غلط|نمیشه|wrong|invalid|incorrect|چیه|یادم رفته)",
         r"(?:نمیتونم|نمیشه).*(?:لاگین|وارد)", r"incorrect username", r"invalid credentials"],
        "اطلاعات ورود پنل.",
        "1️⃣ در Super JinX بار اول: یوزر <code>admin</code> و پسورد <code>admin</code>\n"
        "2️⃣ اگر عوضش کرده‌ای و یادت رفته، Volume را پاک نکن؛ به پشتیبانی پیام بده تا ریست کند.\n"
        "3️⃣ حروف بزرگ و کوچک و فاصله اضافه آخر رمز را چک کن.",
    ),
    (
        [r"reality", r"ریالیتی", r"short ?id", r"public ?key", r"private ?key", r"x25519"],
        "تنظیمات Reality با کانفیگ یکی نیست، یا روی Railway هستی.",
        "1️⃣ ⚠️ Reality روی <b>Railway کار نمی‌کند</b>؛ آنجا از WS یا XHTTP با TLS روی 443 استفاده کن.\n"
        "2️⃣ روی سرور مجازی: SNI کانفیگ با <code>serverNames</code> اینباند یکی باشد.\n"
        "3️⃣ Public Key و Short ID کانفیگ همان مقدار اینباند باشد.\n"
        "4️⃣ بعد از تغییر اینباند، کانفیگ کاربر را دوباره کپی کن.",
    ),
    (
        [r"(?:کانفیگ|config|کانکت|وصل).*(?:نمیشه|نمیشود|نشد|نمیده|قطع|کار نمیکنه|وصل نیست)", r"timeout", r"تایم ?اوت",
         r"i/o timeout", r"context deadline", r"connection (?:refused|reset)", r"پینگ.*(?:نمیده|-1|منفی)", r"ping.*-1"],
        "کانفیگ به سرور نمی‌رسد؛ معمولاً آدرس، SNI یا پورت اشتباه است.",
        "1️⃣ روی Railway: آدرس، <b>SNI</b> و <b>Host</b> کانفیگ هر سه باید <b>دامنه railway</b> باشد و پورت <code>443</code> با <b>TLS</b>.\n"
        "2️⃣ نوع شبکه باید <b>WS</b> یا <b>XHTTP</b> باشد (TCP و Reality روی Railway کار نمی‌کند).\n"
        "3️⃣ مسیر (path) کانفیگ با اینباند یکی باشد.\n"
        "4️⃣ ساعت گوشی را روی خودکار بگذار و اپ را آپدیت کن.\n"
        "5️⃣ با یک اپراتور دیگر هم تست کن.",
    ),
    (
        [r"(?:ساب|sub).*(?:باز نمیشه|خالی|empty|کار نمیکنه|اپدیت نمیشه|ارور|نمیاد|404)", r"subscription.*(?:error|fail)"],
        "سابلینک درست باز نمی‌شود.",
        "1️⃣ لینک را کامل کپی کن (با <code>https://</code>).\n"
        "2️⃣ در اپ، Subscription را Update کن.\n"
        "3️⃣ کاربر فعال باشد و حجم یا تاریخش تمام نشده باشد.\n"
        "4️⃣ اگر دامنه پنل عوض شده، سابلینک جدید را از پنل کپی کن.",
    ),
    (
        [r"(?:ssl|tls|x509|certificate|سرتیفیکیت|گواهی).*(?:error|خطا|ارور|invalid|expired|unknown|نمیده|نمیگیره)",
         r"handshake"],
        "مشکل SSL و گواهی.",
        "1️⃣ روی Railway نیازی به SSL نیست؛ دامنه railway خودش HTTPS دارد.\n"
        "2️⃣ روی سرور مجازی: رکورد A دامنه روی آیپی سرور باشد و پروکسی ابری کلادفلر موقع گرفتن گواهی خاموش.\n"
        "3️⃣ <code>certbot certonly --standalone -d sub.example.com</code>\n"
        "4️⃣ در کانفیگ، SNI همان دامنه گواهی باشد.",
    ),
    (
        [r"(?:کد|code).*(?:تایید|تأیید|verify|verification).*(?:نمیاد|نیومد|نمیرسه)", r"ایمیل.*(?:نمیاد|نیومد)",
         r"captcha", r"کپچا", r"پازل", r"puzzle"],
        "ثبت‌نام GitHub گیر کرده.",
        "1️⃣ پوشه <b>Spam</b> ایمیل را ببین. با <b>Gmail</b> امتحان کن.\n"
        "2️⃣ اگر کپچا لود نمی‌شود: مرورگر را عوض کن (Chrome یا Firefox) و فیلترشکن را عوض کن.\n"
        "3️⃣ حالت ناشناس (Incognito) را امتحان کن.\n"
        "4️⃣ چند دقیقه صبر کن و دوباره «Resend code» بزن.",
    ),
    (
        [r"suspend", r"flag", r"ساسپند", r"بن شد.*(?:گیتهاب|github)", r"(?:گیتهاب|github).*(?:بسته|مسدود|بن)"],
        "اکانت GitHub محدود شده.",
        "1️⃣ از <b>support.github.com</b> تیکت بزن و توضیح بده.\n"
        "2️⃣ تا آن موقع با یک اکانت دیگر کار کن.\n"
        "3️⃣ با اکانت تازه، چند ریپوی پشت سر هم نساز.",
    ),
    (
        [r"(?:اپلود|upload).*(?:نمیشه|نمیشود|نشد|ارور|خطا)", r"file.*too large", r"25 ?mb", r"100 files",
         r"(?:فایل|file).*(?:بزرگ|حجم)"],
        "محدودیت آپلود GitHub.",
        "1️⃣ هر فایل حداکثر <b>25 مگابایت</b> و هر بار حداکثر <b>100 فایل</b>.\n"
        "2️⃣ زیپ را آپلود نکن؛ اول اکسترکت کن و فایل‌ها را بکش داخل صفحه.\n"
        "3️⃣ روی گوشی، مرورگر را روی <b>Desktop site</b> بگذار.",
    ),
    (
        [r"authentication failed", r"permission to .* denied", r"\b403\b", r"rejected", r"non-fast-forward",
         r"support for password authentication"],
        "GitHub رمز را برای git قبول نمی‌کند.",
        "1️⃣ به‌جای رمز از <b>Personal Access Token</b> استفاده کن: Settings ← Developer settings ← Tokens.\n"
        "2️⃣ یا ساده‌تر: فایل‌ها را از خود سایت با <b>Add file ← Upload files</b> آپلود کن.",
    ),
    (
        [r"modulenotfounderror", r"no module named", r"importerror", r"pip.*(?:error|failed)"],
        "یک کتابخانه پایتون نصب نشده.",
        "1️⃣ فایل <code>requirements.txt</code> در ریشه ریپو باشد.\n"
        "2️⃣ اسم ماژولی که در خطا آمده را به آن اضافه کن و کامیت کن.",
    ),
    (
        [r"nginx.*(?:emerg|failed|error)", r"\[emerg\]"],
        "تنظیمات nginx خطا دارد.",
        "1️⃣ فایل <code>nginx.conf.template</code> را با نسخه اصلی عوض کن؛ احتمالاً موقع ادیت یک <code>;</code> یا <code>}</code> جا افتاده.\n"
        "2️⃣ کامیت کن و Deploy Logs را ببین.",
    ),
    (
        [r"address already in use", r"port.*(?:already|in use)", r"bind.*failed"],
        "پورت توسط برنامه دیگری گرفته شده.",
        "1️⃣ روی سرور مجازی: <code>ss -tulpn | grep :443</code> ببین چه برنامه‌ای پورت را گرفته.\n"
        "2️⃣ آن را متوقف کن یا پورت اینباند را عوض کن.",
    ),
    (
        [r"build failed", r"failed to build", r"error.*build", r"بیلد.*(?:ارور|نمیشه|فیل|خطا)", r"deploy(?:ment)? failed",
         r"دیپلوی.*(?:نمیشه|نشد|فیل|ارور|خطا)", r"crash", r"کرش", r"exited with code", r"restarting"],
        "دیپلوی یا بیلد خطا داده.",
        "1️⃣ Railway ← سرویس ← <b>Deployments</b> ← آخرین دیپلوی ← <b>View Logs</b>\n"
        "2️⃣ آخرین خط قرمز را کپی کن و همین‌جا بفرست تا دقیق بگویم مشکل چیست.\n"
        "3️⃣ چک کن <code>Dockerfile</code> در ریشه ریپو باشد و زیپ اکسترکت شده باشد.",
    ),
]
_DIAG = [([re.compile(p, re.I) for p in pats], title, fix) for pats, title, fix in DIAG]

# ---------------------------------------------------------------- گفتگوی کوتاه
GREET = ("سلام", "درود", "هلو", "hello", "hi", "سلامم", "slm", "salam")
THANKS = ("مرسی", "ممنون", "مچکرم", "متشکرم", "دمت گرم", "دمتون گرم", "thanks", "thx", "تشکر", "قربونت", "عالی بود", "حل شد")
WHO = ("کی هستی", "تو کی", "چی هستی", "اسمت چیه", "کی ساختت", "who are you")


def _fuzzy_hit(t: str, kws: list[str]) -> int:
    """امتیاز کلمات کلیدی، با تحمل غلط املایی برای کلمات بلند."""
    score = 0
    words = t.split()
    for k in kws:
        if not k:
            continue
        if k in t:
            score += len(k) * (2 if " " in k else 1)
        elif " " not in k and len(k) >= 5:
            if any(len(w) >= 4 and difflib.SequenceMatcher(None, w, k).ratio() >= 0.84 for w in words):
                score += len(k) - 1
    return score


def best_guide(text: str) -> dict | None:
    t = norm(text)
    best, best_score = None, 0
    for g in db.list_guides():
        kws = [norm(k) for k in re.split(r"[,،]", g["keywords"] or "") if k.strip()]
        s = _fuzzy_hit(t, list(dict.fromkeys(kws)))
        if s > best_score:
            best, best_score = g, s
    return best


def diagnose(text: str) -> tuple[str, str] | None:
    t = (text or "").lower().translate(_FIX)
    for pats, title, fix in _DIAG:
        if any(p.search(t) for p in pats):
            return title, fix
    return None


def small_talk(text: str, name: str) -> str | None:
    t = norm(text)
    words = t.split()
    from utils import brand, support
    if any(w in t for w in WHO):
        return (f"🤖 من <b>جینکس</b> هستم، دستیار هوشمند <b>{brand()}</b>.\n"
                "در نصب پنل، Railway، GitHub، کانفیگ و رفع خطا کمکت می‌کنم.\n"
                "📸 حتی می‌تونی متن خطا رو بفرستی تا بگم کجا رو اشتباه زدی.")
    if any(w in t for w in THANKS) and len(words) <= 6:
        return random.choice([f"🌹 خواهش می‌کنم {name}! موفق باشی.", f"💙 قربانت {name}، هر وقت گیر کردی بپرس.",
                              "✨ خوشحالم که حل شد!"])
    if words and words[0] in GREET and len(words) <= 4:
        return random.choice([
            f"👋 سلام {name}! چه کمکی از دستم برمیاد؟\n🚂 Railway • 🐙 GitHub • ⚡️ پنل • 🧬 کانفیگ",
            f"🌟 سلام {name} جان! مشکلت رو بگو یا متن خطا رو بفرست تا راهنماییت کنم.",
        ])
    return None


def think(text: str, name: str = "دوست من") -> tuple[str, dict | None] | None:
    """جواب مغز داخلی: (متن HTML، راهنمای مرتبط) یا None اگر چیزی برای گفتن ندارد."""
    st = small_talk(text, name)
    if st:
        return st, None
    d = diagnose(text)
    g = best_guide(text)
    if d:
        title, fix = d
        body = f"🔍 <b>تشخیص جینکس:</b> {title}\n━━━━━━━━━━━━━━━\n\n🛠 <b>راه‌حل:</b>\n{fix}\n\n💬 حل نشد؟ متن کامل خطا یا اسکرین‌شات لاگ رو بفرست."
        return body, g
    if g:
        return g["body"], None
    return None
