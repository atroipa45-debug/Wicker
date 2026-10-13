import os
import sqlite3
import time

from config import DB_PATH
from seed import SEED_GUIDES

os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_conn.row_factory = sqlite3.Row
_conn.execute("PRAGMA journal_mode=WAL")
_conn.execute("PRAGMA synchronous=NORMAL")

DEFAULTS = {
    "fj_enabled": "1",
    "welcome_on": "1",
    "welcome_text": "",
    "f_links": "1",
    "f_bad": "1",
    "f_fwd": "1",
    "buy_reply": "1",
    "auto_answer": "1",
    "f_pv": "1",
    "ai_on": "1",
    "ai_mod": "1",
    "ai_vision": "1",
    "ai_all": "0",
    "f_ads": "1",
    "anti_fake": "1",
    "lock": "1",
    "pv_help": "1",
    "brain_on": "1",
    "del_service": "1",
}
_cache: dict[str, str] = {}


def init():
    c = _conn
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT UNIQUE, title TEXT, link TEXT
        );
        CREATE TABLE IF NOT EXISTS guides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, keywords TEXT, body TEXT, pos INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT, first_seen INTEGER);
        CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY, title TEXT);
        CREATE TABLE IF NOT EXISTS badwords (word TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS seen (username TEXT PRIMARY KEY, user_id INTEGER);
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, keywords TEXT, url TEXT
        );
        """
    )
    for k, v in DEFAULTS.items():
        c.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?,?)", (k, v))
    from config import AI_BASE, AI_KEY, AI_MODEL, BRAND, CHANNEL, SUPPORT
    # متغیرهای هوش مصنوعی در Railway همیشه اولویت دارند
    for k, v in (("ai_base", AI_BASE), ("ai_key", AI_KEY), ("ai_model", AI_MODEL)):
        if v:
            c.execute("INSERT OR REPLACE INTO settings(key, value) VALUES (?,?)", (k, v.rstrip("/") if k == "ai_base" else v))
    # مشخصات برند فقط بار اول از متغیرها خوانده می‌شود؛ بعد از پنل قابل تغییر است
    for k, v in (("brand", BRAND), ("channel", CHANNEL), ("support", SUPPORT)):
        if v and not get_setting(k):
            c.execute("INSERT OR REPLACE INTO settings(key, value) VALUES (?,?)", (k, v))
    _cache.clear()
    if get_setting("seed_v") != "2":
        # نسخه ۲: راهنماهای Railway و GitHub؛ راهنماهای قبلی پیش‌فرض جایگزین می‌شوند
        c.execute("DELETE FROM guides")
        for i, (title, kw, body) in enumerate(SEED_GUIDES):
            c.execute("INSERT INTO guides(title, keywords, body, pos) VALUES (?,?,?,?)", (title, kw, body, i))
        set_setting("seed_v", "2")
    c.commit()


# ---------- settings ----------
def get_setting(key, default=None):
    if key in _cache:
        return _cache[key]
    r = _conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    if r:
        _cache[key] = r["value"]
        return r["value"]
    return default


def set_setting(key, value):
    _conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES (?,?)", (key, str(value)))
    _conn.commit()
    _cache[key] = str(value)


def flag(key) -> bool:
    return get_setting(key, DEFAULTS.get(key, "0")) == "1"


def toggle(key):
    set_setting(key, "0" if flag(key) else "1")


# ---------- badwords (کلمات اضافه‌شده توسط ادمین) ----------
_bw_cache: list[str] | None = None


def list_badwords() -> list[str]:
    global _bw_cache
    if _bw_cache is None:
        _bw_cache = [r["word"] for r in _conn.execute("SELECT word FROM badwords ORDER BY word")]
    return _bw_cache


def add_badwords(words):
    global _bw_cache
    for w in words:
        w = w.strip()
        if w:
            _conn.execute("INSERT OR IGNORE INTO badwords(word) VALUES (?)", (w,))
    _conn.commit()
    _bw_cache = None


def del_badword(word):
    global _bw_cache
    _conn.execute("DELETE FROM badwords WHERE word=?", (word,))
    _conn.commit()
    _bw_cache = None


# ---------- channels ----------
_ch_cache: list[dict] | None = None


def list_channels():
    global _ch_cache
    if _ch_cache is None:
        _ch_cache = [dict(r) for r in _conn.execute("SELECT * FROM channels ORDER BY id")]
    return _ch_cache


def add_channel(chat_id, title, link):
    global _ch_cache
    _conn.execute(
        "INSERT OR REPLACE INTO channels(chat_id, title, link) VALUES (?,?,?)", (str(chat_id), title, link)
    )
    _conn.commit()
    _ch_cache = None


def del_channel(cid):
    global _ch_cache
    _conn.execute("DELETE FROM channels WHERE id=?", (cid,))
    _conn.commit()
    _ch_cache = None


# ---------- guides ----------
_g_cache: list[dict] | None = None


def list_guides():
    global _g_cache
    if _g_cache is None:
        _g_cache = [dict(r) for r in _conn.execute("SELECT * FROM guides ORDER BY pos, id")]
    return _g_cache


def _g_reset():
    global _g_cache
    _g_cache = None


def get_guide(gid):
    return next((g for g in list_guides() if g["id"] == gid), None)


def add_guide(title, keywords, body):
    _conn.execute(
        "INSERT INTO guides(title, keywords, body, pos) VALUES (?,?,?,(SELECT IFNULL(MAX(pos),0)+1 FROM guides))",
        (title, keywords, body),
    )
    _conn.commit()
    _g_reset()


def update_guide(gid, field, value):
    if field not in ("title", "keywords", "body"):
        return
    _conn.execute(f"UPDATE guides SET {field}=? WHERE id=?", (value, gid))
    _conn.commit()
    _g_reset()


def del_guide(gid):
    _conn.execute("DELETE FROM guides WHERE id=?", (gid,))
    _conn.commit()
    _g_reset()


# ---------- users / groups ----------
def touch_user(user_id, name):
    _conn.execute(
        "INSERT OR IGNORE INTO users(user_id, name, first_seen) VALUES (?,?,?)", (user_id, name, int(time.time()))
    )
    _conn.commit()


_known_groups: dict[int, str] = {}


def upsert_group(chat_id, title):
    if _known_groups.get(chat_id) == title:
        return
    _conn.execute("INSERT OR REPLACE INTO groups(chat_id, title) VALUES (?,?)", (chat_id, title))
    _conn.commit()
    _known_groups[chat_id] = title


def list_groups():
    return [dict(r) for r in _conn.execute("SELECT * FROM groups ORDER BY title")]


def del_group(chat_id):
    _known_groups.pop(chat_id, None)
    _conn.execute("DELETE FROM groups WHERE chat_id=?", (chat_id,))
    _conn.commit()


def counts():
    q = lambda t: _conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    return {
        "users": q("users"), "groups": q("groups"), "guides": q("guides"),
        "channels": q("channels"), "badwords": q("badwords"),
    }


# ---------- آمار حذف‌ها ----------
def bump(key):
    set_setting(key, int(get_setting(key, "0") or 0) + 1)


# ---------- links (لینک‌های مهم مثل گیتهاب) ----------
_l_cache: list[dict] | None = None


def list_links():
    global _l_cache
    if _l_cache is None:
        _l_cache = [dict(r) for r in _conn.execute("SELECT * FROM links ORDER BY id")]
    return _l_cache


def get_link(lid):
    return next((l for l in list_links() if l["id"] == lid), None)


def add_link(title, keywords, url):
    global _l_cache
    _conn.execute("INSERT INTO links(title, keywords, url) VALUES (?,?,?)", (title, keywords, url))
    _conn.commit()
    _l_cache = None


def del_link(lid):
    global _l_cache
    _conn.execute("DELETE FROM links WHERE id=?", (lid,))
    _conn.commit()
    _l_cache = None


# ---------- یوزرنیم‌های دیده‌شده (برای سکوت و بن با @آیدی) ----------
_seen: dict[str, int] = {}


def remember_user(username: str | None, user_id: int):
    if not username:
        return
    u = username.lower()
    if _seen.get(u) == user_id:
        return
    _seen[u] = user_id
    _conn.execute("INSERT OR REPLACE INTO seen(username, user_id) VALUES (?,?)", (u, user_id))
    _conn.commit()


def find_user(username: str) -> int | None:
    u = username.lower().lstrip("@")
    if u in _seen:
        return _seen[u]
    r = _conn.execute("SELECT user_id FROM seen WHERE username=?", (u,)).fetchone()
    if r:
        _seen[u] = r["user_id"]
        return r["user_id"]
    return None
