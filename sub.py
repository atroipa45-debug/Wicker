"""خواندن و تحلیل سابلینک و ساخت کارت معرفی شیک."""
import base64
import html
import json
import re
import time
from collections import Counter
from urllib.parse import parse_qs, unquote, urlparse

import aiohttp

PROTO_NAMES = {
    "vless": "VLESS", "vmess": "VMess", "trojan": "Trojan", "ss": "Shadowsocks", "ssr": "ShadowsocksR",
    "hysteria2": "Hysteria2", "hy2": "Hysteria2", "hysteria": "Hysteria", "tuic": "TUIC",
    "wireguard": "WireGuard", "wg": "WireGuard", "socks": "SOCKS", "anytls": "AnyTLS",
}
NET_NAMES = {"ws": "WebSocket", "grpc": "gRPC", "xhttp": "XHTTP", "splithttp": "XHTTP", "httpupgrade": "HTTPUpgrade",
             "tcp": "TCP", "raw": "TCP", "h2": "HTTP/2", "http": "HTTP/2", "kcp": "mKCP", "quic": "QUIC"}
FLAG_RE = re.compile(r"[\U0001F1E6-\U0001F1FF]{2}")


def _b64(s: str) -> str:
    s = s.strip().replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s).decode("utf-8", "ignore")


def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) + gd + g_d_m[gm - 1]
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    return jy, jm, jd


FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa(n) -> str:
    return str(n).translate(FA_DIGITS)


def human_bytes(b: int) -> str:
    if b <= 0:
        return "۰"
    units = ["B", "KB", "MB", "GB", "TB"]
    i, v = 0, float(b)
    while v >= 1024 and i < 4:
        v /= 1024
        i += 1
    s = f"{v:.1f}".rstrip("0").rstrip(".")
    return f"{fa(s)} {units[i]}"


def parse_link(line: str) -> dict | None:
    line = line.strip()
    m = re.match(r"^([a-z0-9]+)://", line, re.I)
    if not m:
        return None
    scheme = m.group(1).lower()
    info = {"proto": PROTO_NAMES.get(scheme, scheme.upper()), "net": "", "sec": "", "name": ""}
    try:
        if scheme == "vmess":
            j = json.loads(_b64(line[8:]))
            info.update(net=j.get("net", ""), sec=j.get("tls", ""), name=j.get("ps", ""))
        else:
            u = urlparse(line)
            q = parse_qs(u.query)
            info["net"] = (q.get("type") or [""])[0]
            info["sec"] = (q.get("security") or [""])[0]
            info["name"] = unquote(u.fragment or "")
            if scheme in ("hysteria2", "hy2", "tuic", "hysteria"):
                info["net"], info["sec"] = "quic", "tls"
    except Exception:
        pass
    return info


async def fetch(url: str, proxy: str | None = None) -> dict:
    headers = {"User-Agent": "v2rayNG/1.9.30", "Accept": "*/*"}
    connector = None
    if proxy:
        try:
            from aiohttp_socks import ProxyConnector
            connector = ProxyConnector.from_url(proxy)
        except Exception:
            pass
    async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=20)) as s:
        async with s.get(url, headers=headers, allow_redirects=True, ssl=False) as r:
            body = await r.text(errors="ignore")
            hdr = {k.lower(): v for k, v in r.headers.items()}
            status = r.status
    if status != 200:
        raise RuntimeError(f"HTTP {status}")

    text = body.strip()
    if "://" not in text[:200]:
        try:
            text = _b64(text)
        except Exception:
            pass
    links = [parse_link(l) for l in text.splitlines()]
    links = [l for l in links if l]
    if not links:
        raise RuntimeError("no configs")

    usage = {}
    for part in hdr.get("subscription-userinfo", "").split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            try:
                usage[k.strip()] = int(float(v.strip()))
            except ValueError:
                pass
    title = hdr.get("profile-title", "")
    if title.startswith("base64:"):
        try:
            title = _b64(title[7:])
        except Exception:
            title = ""
    support_url = hdr.get("support-url", "")
    return {"links": links, "usage": usage, "title": title.strip(), "support_url": support_url}


def card(data: dict, intro: str = "", brand: str = "Super JinX") -> tuple[str, str]:
    """متن کارت (HTML) و خلاصه متنی برای هوش مصنوعی را برمی‌گرداند."""
    links = data["links"]
    protos = Counter(l["proto"] for l in links)
    nets = Counter(NET_NAMES.get((l["net"] or "tcp").lower(), l["net"].upper()) for l in links)
    secs = {("Reality" if l["sec"] == "reality" else "TLS" if l["sec"] in ("tls", "xtls") else "") for l in links} - {""}
    flags = []
    for l in links:
        for f in FLAG_RE.findall(l["name"]):
            if f not in flags:
                flags.append(f)

    lines = [f"💎 <b>{html.escape(data['title'] or brand)}</b>", "━━━━━━━━━━━━━━━", ""]
    if intro:
        lines += [intro, ""]
    lines.append(f"📡 <b>تعداد کانفیگ:</b> {fa(len(links))}")
    lines.append("🧬 <b>پروتکل:</b> " + "  •  ".join(f"{p}" + (f" ×{fa(c)}" if c > 1 else "") for p, c in protos.most_common()))
    lines.append("🛰 <b>شبکه:</b> " + "  •  ".join(n for n, _ in nets.most_common()))
    if secs:
        lines.append("🔐 <b>امنیت:</b> " + "  •  ".join(sorted(secs)))
    if flags:
        lines.append("🌍 <b>لوکیشن:</b> " + " ".join(flags[:12]))

    u = data["usage"]
    total, used = u.get("total", 0), u.get("upload", 0) + u.get("download", 0)
    if total:
        pct = min(100, round(used * 100 / total)) if total else 0
        bar = "▰" * round(pct / 10) + "▱" * (10 - round(pct / 10))
        lines.append(f"📊 <b>حجم:</b> {human_bytes(total)}  (مصرف: {human_bytes(used)})")
        lines.append(f"{bar} {fa(pct)}٪")
    elif "total" in u:
        lines.append("📊 <b>حجم:</b> نامحدود ♾")
    exp = u.get("expire", 0)
    if exp:
        t = time.gmtime(exp)
        jy, jm, jd = gregorian_to_jalali(t.tm_year, t.tm_mon, t.tm_mday)
        left = int((exp - time.time()) // 86400)
        left_txt = f"{fa(left)} روز مانده" if left >= 0 else "منقضی شده"
        lines.append(f"⏳ <b>انقضا:</b> {fa(jy)}/{fa(f'{jm:02d}')}/{fa(f'{jd:02d}')}  ({left_txt})")
    elif "expire" in u:
        lines.append("⏳ <b>انقضا:</b> بدون محدودیت زمانی ♾")
    lines += ["", "📲 سابلینک را کپی کنید و در برنامه <b>Import from clipboard</b> بزنید.",
              "⚡️ <i>v2rayNG • Hiddify • Streisand • V2Box</i>"]

    summary = (
        f"نام: {data['title'] or brand}\nتعداد کانفیگ: {len(links)}\n"
        f"پروتکل‌ها: {', '.join(protos)}\nشبکه: {', '.join(nets)}\nامنیت: {', '.join(secs) or '-'}\n"
        f"لوکیشن: {' '.join(flags) or '-'}\nحجم: {human_bytes(total) if total else 'نامحدود'}"
    )
    return "\n".join(lines), summary
