# راهنماهای پیش‌فرض؛ ادمین از داخل ربات می‌تواند ویرایش، حذف یا اضافه کند.
# ترتیب مهم است: در امتیاز برابر، راهنمای بالاتر انتخاب می‌شود.
RW = "railway,ریلوی,رلوی,ریل وی,رل وی,ریلوی,ریلوای,ریلوِی"
GH = "github,گیتهاب,گیت هاب,گیتاب,گیتاپ,گیت هب,گیتهب"

SEED_GUIDES = [
    (
        "🛠 رفع مشکلات Railway",
        RW + ",build failed,crashed,crash,کرش,بیلد,502,application failed,healthcheck,هلث چک,بالا نمیاد,ردیپلوی,redeploy,deploy failed,دیپلوی نشد,trial,ترایال,limited",
        "🛠 <b>رفع مشکلات Railway</b>\n\n"
        "🔴 <b>Build Failed</b>\n"
        "▫️ لاگ Build را باز کنید و خط قرمز آخر را ببینید.\n"
        "▫️ فایل <code>Dockerfile</code> باید در <b>ریشه ریپو</b> باشد، نه داخل پوشه. اگر داخل پوشه است: Settings ← Root Directory.\n"
        "▫️ زیپ را حتماً <b>اکسترکت</b> کنید و فایل‌ها را آپلود کنید، نه خود زیپ را.\n\n"
        "🟠 <b>exec format error / no such file / permission denied</b>\n"
        "▫️ فایل‌ها با گوشی یا ویندوز ادیت شده و خط‌بندی خراب شده. این خط را در Dockerfile قبل از ENTRYPOINT بگذارید:\n"
        "<code>RUN sed -i 's/\\r$//' /entrypoint.sh &amp;&amp; chmod +x /entrypoint.sh</code>\n\n"
        "🟡 <b>Application failed to respond / 502</b>\n"
        "▫️ Settings ← Networking ← روی دامنه بزنید و <b>Target Port</b> را روی پورت برنامه بگذارید (Super JinX: <code>8080</code>).\n"
        "▫️ چند دقیقه بعد از دیپلوی صبر کنید؛ بالا آمدن اول کمی طول می‌کشد.\n\n"
        "🟢 <b>Healthcheck failed</b>\n"
        "▫️ مسیر هلث‌چک در <code>railway.json</code> باید درست باشد (Super JinX: <code>/healthz</code>) و پورت هم درست تنظیم شده باشد.\n\n"
        "🔵 <b>Crashed / مدام ری‌استارت</b>\n"
        "▫️ Deploy Logs را ببینید؛ معمولاً یک متغیر (Variables) جا افتاده یا اشتباه است.\n\n"
        "🟣 <b>بعد از ردیپلوی اطلاعات پاک شد</b>\n"
        "▫️ <b>Volume</b> نساخته‌اید. روی سرویس: Add Volume و مسیر را بگذارید روی پوشه دیتای پنل (Super JinX: <code>/var/lib/pasarguard</code>).\n\n"
        "⚪️ <b>Trial تمام شد / Limited Trial</b>\n"
        "▫️ از بخش Usage اعتبار را چک کنید. با اکانت محدود، معمولاً اول باید اکانت گیتهاب تأیید شود یا پلن Hobby فعال شود.\n\n"
        "💬 حل نشد؟ اسکرین‌شات لاگ را در گروه بفرستید.",
    ),
    (
        "🚂 دیپلوی پنل روی Railway",
        RW + ",deploy,دیپلوی,دپلوی,ولوم,volume,دامنه railway,generate domain,اموزش railway,نصب روی railway",
        "🚂 <b>دیپلوی پنل روی Railway</b>\n\n"
        "1️⃣ فایل‌های پنل را در یک ریپوی <b>GitHub</b> آپلود کنید (فایل‌ها در ریشه ریپو باشند).\n\n"
        "2️⃣ وارد railway.com شوید ← <b>New Project</b> ← <b>Deploy from GitHub repo</b> و ریپو را انتخاب کنید.\n"
        "▫️ ریپو را نمی‌بینید؟ گزینه <b>Configure GitHub App</b> را بزنید و به ریپو دسترسی بدهید.\n\n"
        "3️⃣ <b>Volume</b> بسازید تا اطلاعات پاک نشود:\n"
        "▫️ روی سرویس ← Add Volume ← مسیر: <code>/var/lib/pasarguard</code> (برای Super JinX)\n\n"
        "4️⃣ دامنه بگیرید:\n"
        "▫️ Settings ← Networking ← <b>Generate Domain</b> ← پورت <code>8080</code>\n\n"
        "5️⃣ صبر کنید تا وضعیت <b>Active</b> و سبز شود، بعد دامنه را باز کنید.\n\n"
        "🔐 در Super JinX یوزر و پسورد اولیه <code>admin</code> / <code>admin</code> است؛ <b>همان اول عوضش کنید.</b>\n\n"
        "💡 Railway فقط HTTP/HTTPS می‌دهد؛ پس کانفیگ‌ها باید از نوع <b>WS</b>، <b>XHTTP</b> یا <b>gRPC</b> روی پورت 443 باشند. Reality روی Railway کار نمی‌کند.",
    ),
    (
        "🧩 رفع مشکلات GitHub",
        GH + ",ثبت نام,sign up,signup,verify,وریفای,کد تایید,کد تأیید,کپچا,captcha,puzzle,پازل,suspend,ساسپند,flag,فلگ,404,not found,private,پرایوت,25mb,حجم",
        "🧩 <b>رفع مشکلات GitHub</b>\n\n"
        "📧 <b>کد تأیید ایمیل نمی‌آید</b>\n"
        "▫️ پوشه Spam را چک کنید. با Gmail امتحان کنید و چند دقیقه صبر کنید.\n\n"
        "🧠 <b>کپچا یا پازل لود نمی‌شود</b>\n"
        "▫️ مرورگر را عوض کنید (Chrome یا Firefox)، فیلترشکن را عوض کنید و حالت ناشناس را امتحان کنید.\n\n"
        "🚫 <b>اکانت Flag یا Suspend شد</b>\n"
        "▫️ از support.github.com تیکت بزنید. با اکانت تازه و خالی سریع ریپو نسازید.\n\n"
        "📦 <b>فایل آپلود نمی‌شود</b>\n"
        "▫️ هر فایل حداکثر 25 مگابایت و هر بار حداکثر 100 فایل.\n"
        "▫️ زیپ را آپلود نکنید؛ اول اکسترکت کنید.\n\n"
        "🔎 <b>ریپو در Railway دیده نمی‌شود</b>\n"
        "▫️ در Railway گزینه Configure GitHub App را بزنید و به ریپو یا All repositories دسترسی بدهید.\n\n"
        "❗️ <b>ارور 404 یا فایل پیدا نشد</b>\n"
        "▫️ اسم فایل‌ها به حروف بزرگ و کوچک حساس است؛ <code>Dockerfile</code> با <code>dockerfile</code> فرق دارد.",
    ),
    (
        "📤 ساخت ریپو و آپلود در GitHub",
        GH + ",ریپو,repo,repository,ریپازیتوری,اپلود,آپلود,upload,کامیت,commit,فورک,fork",
        "📤 <b>ساخت ریپو و آپلود فایل در GitHub</b>\n\n"
        "1️⃣ وارد github.com شوید ← دکمه <b>+</b> بالای صفحه ← <b>New repository</b>\n"
        "2️⃣ یک اسم بدهید و <b>Create repository</b> را بزنید.\n"
        "3️⃣ روی <b>uploading an existing file</b> یا <b>Add file ← Upload files</b> بزنید.\n"
        "4️⃣ زیپ را روی گوشی یا کامپیوتر <b>اکسترکت</b> کنید و همه فایل‌ها را بکشید داخل صفحه.\n"
        "5️⃣ پایین صفحه <b>Commit changes</b> را بزنید.\n\n"
        "📱 روی گوشی: مرورگر را روی <b>Desktop site</b> بگذارید تا گزینه آپلود کامل نمایش داده شود.\n\n"
        "✅ هر بار فایلی را در ریپو عوض کنید، Railway خودکار دوباره دیپلوی می‌کند.",
    ),
    (
        "⚡️ نصب پنل مرزبان",
        "مرزبان,marzban",
        "⚡️ <b>نصب پنل مرزبان (Marzban)</b>\n\n"
        "🖥 پیش‌نیاز: سرور با Ubuntu 22.04 یا جدیدتر و دسترسی root\n\n"
        "1️⃣ <b>نصب</b>\n"
        "<code>sudo bash -c \"$(curl -sL https://github.com/Gozargah/Marzban-scripts/raw/master/marzban.sh)\" @ install</code>\n\n"
        "2️⃣ <b>ساخت ادمین</b>\n"
        "<code>marzban cli admin create --sudo</code>\n\n"
        "3️⃣ <b>ورود به پنل</b>\n"
        "<code>http://IP:8000/dashboard/</code>\n\n"
        "🧰 <b>دستورهای کاربردی</b>\n"
        "<code>marzban restart</code> ری‌استارت\n"
        "<code>marzban logs</code> لاگ‌ها\n"
        "<code>marzban update</code> آپدیت\n\n"
        "🔐 برای امنیت، پنل را پشت دامنه و SSL ببرید.",
    ),
    (
        "🌀 نصب پنل ثنایی (3x-ui)",
        "ثنایی,سنایی,3x-ui,3xui,x-ui,xui",
        "🌀 <b>نصب پنل ثنایی (3x-ui)</b>\n\n"
        "1️⃣ <b>نصب</b>\n"
        "<code>bash &lt;(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)</code>\n\n"
        "📝 آخر نصب، نام کاربری، رمز، پورت و مسیر پنل نمایش داده می‌شود؛ حتماً یادداشت کنید.\n\n"
        "2️⃣ <b>منوی مدیریت</b>\n"
        "<code>x-ui</code>\n\n"
        "🧰 <b>دستورهای کاربردی</b>\n"
        "<code>x-ui restart</code> ری‌استارت\n"
        "<code>x-ui log</code> لاگ‌ها",
    ),
    (
        "🌐 نصب پنل هیدیفای",
        "هیدیفای,hiddify",
        "🌐 <b>نصب پنل هیدیفای (Hiddify Manager)</b>\n\n"
        "<code>bash &lt;(curl i.hiddify.com/release)</code>\n\n"
        "🔗 بعد از نصب، لینک ورود به پنل نمایش داده می‌شود؛ جای امن نگهش دارید.\n"
        "💡 روی Ubuntu 22.04 یا 24.04 تمیز (بدون پنل دیگر) نصب کنید.",
    ),
    (
        "🧬 انواع کانفیگ و پروتکل",
        "کانفیگ,config,ریالیتی,reality,vless,vmess,trojan,ویلس,ویمس,تروجان,پروتکل,اینباند,inbound,xhttp,grpc",
        "🧬 <b>انواع کانفیگ</b>\n\n"
        "💎 <b>VLESS + Reality</b>: بدون دامنه، پایدار؛ روی سرور مجازی پیشنهاد اول. (روی Railway کار نمی‌کند)\n\n"
        "☁️ <b>VLESS + WS + TLS</b>: مناسب Railway و CDN. پورت 443.\n\n"
        "🚀 <b>XHTTP / gRPC</b>: وقتی WS کند یا ناپایدار است.\n\n"
        "🛡 <b>Trojan + TLS</b>: سبک و ساده، نیاز به دامنه و SSL.\n\n"
        "⏱ VMess به ساعت حساس است؛ ساعت سرور و گوشی باید درست باشد.",
    ),
    (
        "🔌 رفع مشکل وصل نشدن کانفیگ",
        "وصل نمیشه,وصل نمی شه,وصل نمیشود,وصل نشد,قطع,پینگ,ping,timeout,کانکت,connect",
        "🔌 <b>چک‌لیست وصل نشدن کانفیگ</b>\n\n"
        "1️⃣ ساعت گوشی را روی خودکار بگذارید.\n"
        "2️⃣ اگر روی Railway هستید: آدرس و SNI و Host کانفیگ باید <b>دامنه railway</b> باشد و پورت <code>443</code> با TLS.\n"
        "3️⃣ روی سرور مجازی: پورت در فایروال باز باشد\n<code>ufw allow 443/tcp</code>\n"
        "4️⃣ لاگ پنل را ببینید.\n"
        "5️⃣ در Reality، SNI و Public Key کانفیگ با اینباند یکی باشد.\n"
        "6️⃣ اپ کلاینت را آپدیت کنید.\n\n"
        "💬 حل نشد؟ متن خطا یا اسکرین‌شات را بفرستید.",
    ),
    (
        "📱 برنامه‌های کلاینت",
        "کلاینت,client,v2rayng,v2rayn,streisand,v2box,nekobox,nekoray,اندروید,ایفون,ios,ویندوز,سابلینک,ساب لینک,subscription",
        "📱 <b>برنامه‌های پیشنهادی</b>\n\n"
        "🤖 <b>اندروید:</b> v2rayNG، Hiddify، NekoBox\n"
        "🍎 <b>آیفون:</b> Streisand، V2Box، Hiddify\n"
        "💻 <b>ویندوز:</b> v2rayN، Hiddify\n"
        "🖥 <b>مک:</b> V2Box، Hiddify\n\n"
        "📋 کانفیگ یا سابلینک را کپی کنید و در برنامه <b>Import from clipboard</b> بزنید.",
    ),
    (
        "🔒 دامنه و SSL",
        "ssl,سرتیفیکیت,certificate,certbot,acme,گواهی,کلادفلر,cloudflare,cdn",
        "🔒 <b>گرفتن SSL رایگان</b>\n\n"
        "1️⃣ رکورد A دامنه را روی آیپی سرور بگذارید (موقع گرفتن گواهی، پروکسی ابری کلادفلر خاموش).\n\n"
        "2️⃣ <code>apt install certbot -y\ncertbot certonly --standalone -d sub.example.com</code>\n\n"
        "📂 مسیر فایل‌ها:\n"
        "<code>/etc/letsencrypt/live/sub.example.com/fullchain.pem\n/etc/letsencrypt/live/sub.example.com/privkey.pem</code>\n\n"
        "💡 روی Railway نیازی به SSL نیست؛ خودش دامنه HTTPS می‌دهد.",
    ),
    (
        "🚀 افزایش سرعت (BBR)",
        "bbr,سرعت,کنده,اسپید,speed",
        "🚀 <b>فعال کردن BBR</b> (فقط سرور مجازی)\n\n"
        "<code>echo \"net.core.default_qdisc=fq\" &gt;&gt; /etc/sysctl.conf\n"
        "echo \"net.ipv4.tcp_congestion_control=bbr\" &gt;&gt; /etc/sysctl.conf\n"
        "sysctl -p</code>\n\n"
        "✅ بررسی:\n<code>sysctl net.ipv4.tcp_congestion_control</code>",
    ),
]
