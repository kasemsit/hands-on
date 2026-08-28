#!/usr/bin/env python3
"""
Lab server สำหรับฝึก curl / cookie / session / CSRF / redirect / JSON API / PoW CAPTCHA

รัน:  python3 lab/server.py
เปิด: http://127.0.0.1:8080

ใช้ stdlib ล้วน ไม่ต้อง pip install อะไรเลย
เก็บ state ไว้ใน memory เท่านั้น (รีสตาร์ท = ล้างหมด) เพราะเป็นแค่ของฝึก
"""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8080

# endpoint SSRF ในบทที่ 25 มีช่องโหว่โดยเจตนา จึงปิดไว้เป็นค่าเริ่มต้น
# เปิดตอนทำแบบฝึกหัดด้วย: LAB_ENABLE_SSRF=1 python3 lab/server.py
ENABLE_SSRF_LAB = os.environ.get("LAB_ENABLE_SSRF") == "1"

# key สำหรับ sign challenge - เว็บจริงต้องเก็บเป็นความลับฝั่ง server เท่านั้น
HMAC_KEY = secrets.token_bytes(32)

# in-memory stores
SESSIONS = {}   # sid -> dict
SOLVED = {}     # pow_token -> expiry timestamp
TOKENS = {}     # access token -> {"user": ..., "exp": ...}
REFRESH = {}    # refresh token -> {"user":..., "exp":..., "family":..., "used": bool}

# ⚠️ ของจริงต้อง hash ด้วย Argon2id/bcrypt เก็บ plain text แบบนี้เพื่อให้อ่านโค้ดง่ายเท่านั้น
USERS = {"myuser": "mypass", "otheruser": "otherpass"}

# API key แบบ static - เว็บจริงจะ generate ต่อผู้ใช้และ revoke ได้
API_KEYS = {"demo-key-123": "myuser", "other-key-456": "someone"}

BOOKS = [
    {"id": 1, "title": "Everything curl", "author": "Daniel Stenberg", "tag": "curl"},
    {"id": 2, "title": "HTTP: The Definitive Guide", "author": "Gourley & Totty", "tag": "http"},
    {"id": 3, "title": "ประวัติศาสตร์อินเทอร์เน็ต", "author": "สมชาย", "tag": "หนังสือ"},
    {"id": 4, "title": "Web Scraping with Python", "author": "Ryan Mitchell", "tag": "python"},
    {"id": 5, "title": "Bot or Not", "author": "Anti Bot", "tag": "antibot"},
]

# ข้อมูลสำหรับบทที่ 24 (BOLA/IDOR) - แต่ละ order มีเจ้าของ
# amount เป็น "สตางค์" ตามหลักในบทที่ 12 (ห้ามใช้ float กับเงิน)
ORDERS = {
    1001: {"id": 1001, "owner": "myuser",    "item": "Everything curl",       "amount": 45000},
    1002: {"id": 1002, "owner": "otheruser", "item": "API Security in Action", "amount": 189000},
    1003: {"id": 1003, "owner": "myuser",    "item": "Bot or Not",             "amount": 32000},
    1004: {"id": 1004, "owner": "otheruser", "item": "Real-World Cryptography", "amount": 175000},
}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def html_page(title, body):
    return f"""<!doctype html>
<html lang="th">
<head><meta charset="utf-8"><title>{title}</title>
<style>
 body{{font-family:system-ui,sans-serif;max-width:52rem;margin:2rem auto;padding:0 1rem;line-height:1.6}}
 code,pre{{background:#f4f4f5;padding:.15em .35em;border-radius:4px}}
 pre{{padding:1rem;overflow:auto}}
 input,select,button{{font:inherit;padding:.35rem;margin:.2rem 0}}
 .box{{border:1px solid #ddd;border-radius:8px;padding:1rem;margin:1rem 0}}
</style>
</head>
<body>
<h1>{title}</h1>
{body}
<hr><p><a href="/">&larr; หน้าแรก lab</a></p>
</body></html>"""


def parse_cookies(header):
    """แปลง header 'Cookie: a=1; b=2' เป็น dict"""
    out = {}
    if not header:
        return out
    for part in header.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def parse_multipart(body, boundary):
    """multipart parser แบบง่าย พอสำหรับ lab (ไม่ครบ spec)"""
    fields = {}
    files = {}
    sep = b"--" + boundary
    for chunk in body.split(sep):
        chunk = chunk.strip(b"\r\n")
        if not chunk or chunk == b"--":
            continue
        if b"\r\n\r\n" not in chunk:
            continue
        raw_headers, content = chunk.split(b"\r\n\r\n", 1)
        headers = raw_headers.decode("utf-8", "replace")
        name = None
        filename = None
        for line in headers.split("\r\n"):
            if line.lower().startswith("content-disposition"):
                for piece in line.split(";"):
                    piece = piece.strip()
                    if piece.startswith('name="'):
                        name = piece[6:-1]
                    elif piece.startswith('filename="'):
                        filename = piece[10:-1]
        if name is None:
            continue
        if filename is not None:
            files[name] = (filename, len(content))
        else:
            fields[name] = content.decode("utf-8", "replace")
    return fields, files


def make_challenge(difficulty=50_000):
    """
    สร้าง PoW challenge แบบเดียวกับ ALTCHA v1:
      challenge = sha256(salt + number)
      signature = HMAC-SHA256(server_key, challenge)
    client ต้องหา number ที่ทำให้ hash ตรง โดยลองตั้งแต่ 0..maxNumber
    """
    salt = secrets.token_hex(8) + "?expires=" + str(int(time.time()) + 600)
    number = secrets.randbelow(difficulty)
    challenge = hashlib.sha256(f"{salt}{number}".encode()).hexdigest()
    signature = hmac.new(HMAC_KEY, challenge.encode(), hashlib.sha256).hexdigest()
    return {
        "algorithm": "SHA-256",
        "challenge": challenge,
        "maxNumber": difficulty,
        "salt": salt,
        "signature": signature,
    }


def issue_token_pair(user, family):
    """
    ออก access token (อายุสั้น) + refresh token (อายุยาว) เป็นคู่
    family = กลุ่มของ token ที่สืบทอดมาจากการ login ครั้งเดียวกัน
             ใช้เพื่อเพิกถอนทั้งสายได้ตอนตรวจพบ token รั่ว
    """
    access = secrets.token_urlsafe(24)
    refresh = secrets.token_urlsafe(32)
    TOKENS[access] = {"user": user, "exp": time.time() + 120, "family": family}
    REFRESH[refresh] = {"user": user, "exp": time.time() + 3600, "family": family, "used": False}
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "Bearer",
        "expires_in": 120,
    }


def verify_payload(payload_b64):
    """
    ตรวจ payload จาก client
    payload = base64( json({algorithm, challenge, number, salt, signature}) )
    ซึ่งเป็นรูปแบบจริงของ ALTCHA v1 (widget ส่ง base64 string ไม่ใช่ JSON object)
    """
    try:
        raw = base64.b64decode(payload_b64)
        data = json.loads(raw)
    except Exception:
        return False, "payload ไม่ใช่ base64 ของ JSON"

    for key in ("algorithm", "challenge", "number", "salt", "signature"):
        if key not in data:
            return False, f"payload ขาด field: {key}"

    if data["algorithm"].upper() != "SHA-256":
        return False, "algorithm ไม่รองรับ"

    # 1) signature ต้องเป็นของ server เราจริง (กันคนปลอม challenge เอง)
    expect_sig = hmac.new(HMAC_KEY, data["challenge"].encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expect_sig, data["signature"]):
        return False, "signature ไม่ถูกต้อง"

    # 2) salt ต้องยังไม่หมดอายุ
    qs = urllib.parse.parse_qs(data["salt"].split("?", 1)[-1])
    expires = qs.get("expires", ["0"])[0]
    if int(expires) < time.time():
        return False, "challenge หมดอายุแล้ว"

    # 3) number ต้อง hash ได้ตรง challenge
    check = hashlib.sha256(f"{data['salt']}{data['number']}".encode()).hexdigest()
    if not hmac.compare_digest(check, data["challenge"]):
        return False, "number ไม่ถูกต้อง (PoW ไม่ผ่าน)"

    return True, "ok"


# --------------------------------------------------------------------------
# handler
# --------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "LabServer/1.0"
    protocol_version = "HTTP/1.1"

    # ---------- utils ----------
    def send(self, code, body, ctype="text/html; charset=utf-8", extra_headers=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra_headers or []):
            self.send_header(k, v)
        self.end_headers()
        # HEAD ตอบ header เหมือน GET ทุกอย่าง แต่ไม่ส่ง body
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_json(self, code, obj, extra_headers=None):
        self.send(code, json.dumps(obj, ensure_ascii=False, indent=2),
                  "application/json; charset=utf-8", extra_headers)

    def redirect(self, location, extra_headers=None):
        self.send(302, f'<a href="{location}">moved</a>',
                  extra_headers=[("Location", location)] + (extra_headers or []))

    def cookies(self):
        return parse_cookies(self.headers.get("Cookie"))

    def session(self, create=False):
        """คืน (sid, session_dict, set_cookie_header_or_None)"""
        sid = self.cookies().get("sid")
        if sid and sid in SESSIONS:
            return sid, SESSIONS[sid], None
        if not create:
            return None, None, None
        sid = secrets.token_hex(16)
        SESSIONS[sid] = {"csrf": secrets.token_hex(16), "auth": False}
        # HttpOnly = JS อ่านไม่ได้ / Path=/ = ส่งไปทุก path
        return sid, SESSIONS[sid], ("Set-Cookie", f"sid={sid}; Path=/; HttpOnly")

    def read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length else b""

    def form_body(self):
        return dict(urllib.parse.parse_qsl(self.read_body().decode("utf-8")))

    def log_message(self, fmt, *args):
        print(f"  {self.command:6} {self.path:40} -> {args[1] if len(args) > 1 else ''}")

    # ---------- routing ----------
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
        routes = {
            "/": self.page_index,
            "/headers": self.page_headers,
            "/login": self.page_login_form,
            "/dashboard": self.page_dashboard,
            "/search": self.page_search_form,
            "/upload": self.page_upload_form,
            "/slow": self.page_slow,
            "/spa": self.page_spa,
            "/api/spa-data": self.api_spa_data,
            "/api/challenge": self.api_challenge,
            "/api/protected": self.api_protected,
            "/api/books": self.api_books,
            "/basic": self.page_basic_auth,
            "/api/keyed": self.api_keyed,
            "/api/me": self.api_me,
            "/api/echo-ip": self.api_echo_ip,
            "/api/cached": self.api_cached,
            "/api/stream": self.api_stream,
            "/api/fetch": self.api_fetch,
        }
        fn = routes.get(path)
        if fn:
            return fn(query)

        # route ที่มี id อยู่ใน path - ต้องจับด้วย regex ไม่ใช่ dict
        m = re.fullmatch(r"/api/(v1|v2)/orders/(\d+)", path)
        if m:
            return self.api_order(m.group(1), int(m.group(2)))

        self.send(404, html_page("404", "<p>ไม่มีหน้านี้</p>"))

    def do_HEAD(self):
        # ใช้ routing เดียวกับ GET - send() จะไม่เขียน body ให้เอง
        self.do_GET()

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        routes = {
            "/login": self.post_login,
            "/search": self.post_search,
            "/upload": self.post_upload,
            "/api/solution": self.post_solution,
            "/api/token": self.post_token,
            "/api/refresh": self.post_refresh,
        }
        fn = routes.get(path)
        if fn:
            return fn()
        self.send(404, html_page("404", "<p>ไม่มีหน้านี้</p>"))

    # ---------- pages ----------
    def page_index(self, q):
        self.send(200, html_page("Lab Server สำหรับฝึก curl", """
<p>ทุก endpoint ที่นี่ออกแบบให้ฝึกทีละเรื่อง ลองยิงด้วย <code>curl</code> ได้เลย</p>
<div class="box">
<h3>บทที่ 1-2 · HTTP + curl พื้นฐาน</h3>
<ul>
  <li><code>GET /headers</code> — echo header ที่คุณส่งมา (ฝึก <code>-H</code>, <code>-A</code>)</li>
  <li><code>GET /slow</code> — ตอบช้า 3 วิ (ฝึก <code>--max-time</code>)</li>
  <li><code>GET /api/books?tag=curl</code> — JSON API (ฝึก <code>jq</code>)</li>
</ul>
</div>
<div class="box">
<h3>บทที่ 3-5 · Form + Cookie + Redirect</h3>
<ul>
  <li><a href="/login">GET /login</a> — form มี CSRF token ซ่อนอยู่ + ตั้ง cookie <code>sid</code></li>
  <li><code>POST /login</code> — ถูกต้องแล้ว <b>302 redirect</b> ไป <code>/dashboard</code></li>
  <li><a href="/dashboard">GET /dashboard</a> — ต้อง login ก่อน</li>
  <li><a href="/search">GET /search</a> + <code>POST /search</code> — urlencoded + ภาษาไทย</li>
  <li><a href="/upload">GET /upload</a> + <code>POST /upload</code> — multipart/form-data</li>
</ul>
</div>
<div class="box">
<h3>บทที่ 7-8 · Authentication (API key / Bearer / Basic)</h3>
<ul>
  <li><a href="/basic">GET /basic</a> — HTTP Basic auth (<code>curl -u myuser:mypass</code>)</li>
  <li><code>GET /api/keyed</code> — ต้องมี header <code>X-API-Key: demo-key-123</code></li>
  <li><code>POST /api/token</code> — แลก user/pass เป็น access + refresh token</li>
  <li><code>GET /api/me</code> — ต้องมี <code>Authorization: Bearer &lt;token&gt;</code> (access token อายุ 2 นาที)</li>
  <li><code>POST /api/refresh</code> — หมุน refresh token ใบใหม่ + ตรวจจับการใช้ซ้ำ</li>
</ul>
</div>
<div class="box">
<h3>บทที่ 9 · CAPTCHA แบบ Proof of Work</h3>
<ul>
  <li><code>GET /api/challenge</code> — ขอโจทย์ (แบบเดียวกับ ALTCHA v1)</li>
  <li><code>POST /api/solution</code> — ส่งคำตอบ <code>{"captcha": "&lt;base64&gt;"}</code></li>
  <li><code>GET /api/protected</code> — เข้าได้เมื่อผ่าน PoW แล้วเท่านั้น</li>
</ul>
</div>
<div class="box">
<h3>บทที่ 17-18 · ทำไมต้อง Playwright</h3>
<ul>
  <li><a href="/spa">GET /spa</a> — หน้าที่ HTML ว่างเปล่า เนื้อหามาจาก JS
      (<code>curl</code> จะไม่เห็นอะไรเลย)</li>
</ul>
</div>
<div class="box">
<h3>บทที่ 24-29 · Authorization, proxy, cache, stream</h3>
<ul>
  <li><code>GET /api/v1/orders/1002</code> — <b>มีช่องโหว่ BOLA โดยเจตนา</b>
      (token ของใครก็ดู order ของคนอื่นได้)</li>
  <li><code>GET /api/v2/orders/1002</code> — เวอร์ชันที่แก้แล้ว</li>
  <li><code>GET /api/echo-ip</code> — เห็น <code>remote_addr</code> เทียบกับ
      <code>X-Forwarded-For</code></li>
  <li><code>GET /api/cached</code> — ETag + 304 Not Modified</li>
  <li><code>GET /api/stream</code> — Server-Sent Events (ลองด้วย <code>curl -N</code>)</li>
  <li><code>GET /api/fetch?url=</code> — <b>SSRF โดยเจตนา</b>
      (ต้องเปิดด้วย <code>LAB_ENABLE_SSRF=1</code>)</li>
</ul>
</div>
"""))

    def page_headers(self, q):
        lines = [f"{k}: {v}" for k, v in self.headers.items()]
        self.send_json(200, {
            "method": self.command,
            "path": self.path,
            "headers": dict(self.headers.items()),
            "raw": lines,
        })

    def page_slow(self, q):
        time.sleep(3)
        self.send(200, html_page("ช้าแต่มาแล้ว", "<p>รอ 3 วินาที</p>"))

    def api_books(self, q):
        tag = q.get("tag")
        items = [b for b in BOOKS if not tag or b["tag"] == tag]
        self.send_json(200, {"count": len(items), "items": items})

    # ---------- login flow ----------
    def page_login_form(self, q):
        sid, sess, setcookie = self.session(create=True)
        body = f"""
<p>user: <code>myuser</code> / pass: <code>mypass</code></p>
<form method="POST" action="/login">
  <input type="hidden" name="csrf_token" value="{sess['csrf']}">
  <label>username <input name="username"></label><br>
  <label>password <input name="password" type="password"></label><br>
  <button type="submit">Login</button>
</form>
<p>CSRF token ของ session นี้คือ <code>{sess['csrf']}</code>
   — ผูกกับ cookie <code>sid</code> ที่เพิ่งตั้งให้</p>
"""
        self.send(200, html_page("Login", body),
                  extra_headers=[setcookie] if setcookie else None)

    def post_login(self):
        sid, sess, _ = self.session()
        if not sess:
            return self.send(403, html_page("403", "<p>ไม่มี session cookie — ต้อง GET /login ก่อน</p>"))
        form = self.form_body()
        if form.get("csrf_token") != sess["csrf"]:
            return self.send(403, html_page("403", "<p>CSRF token ไม่ถูกต้อง</p>"))
        if USERS.get(form.get("username")) != form.get("password"):
            return self.send(401, html_page("401", '<p>user/pass ผิด <a href="/login">ลองใหม่</a></p>'))
        sess["auth"] = True
        sess["user"] = form["username"]
        # หมุน CSRF token ใหม่หลัง login (session fixation hygiene)
        sess["csrf"] = secrets.token_hex(16)
        self.redirect("/dashboard")

    def page_dashboard(self, q):
        sid, sess, _ = self.session()
        if not sess or not sess.get("auth"):
            return self.send(401, html_page("401", '<p>ยังไม่ได้ login — ไปที่ <a href="/login">/login</a></p>'))
        self.send(200, html_page("Dashboard", f"""
<p>สวัสดี <b>{sess['user']}</b> 🎉 คุณผ่าน login + cookie + redirect ครบแล้ว</p>
<p>session id: <code>{sid}</code></p>
<p>ลองต่อที่ <a href="/search">/search</a></p>
"""))

    # ---------- search ----------
    def page_search_form(self, q):
        sid, sess, setcookie = self.session(create=True)
        body = f"""
<form method="POST" action="/search">
  <input type="hidden" name="csrf_token" value="{sess['csrf']}">
  <label>คำค้น <input name="query" placeholder="เช่น curl หรือ หนังสือ"></label>
  <select name="field">
    <option value="title">title</option>
    <option value="author">author</option>
    <option value="tag">tag</option>
  </select>
  <button type="submit">ค้นหา</button>
</form>
<p>ลองพิมพ์คำที่มี space หรือภาษาไทย เพื่อดูว่าทำไมต้องใช้ <code>--data-urlencode</code></p>
"""
        self.send(200, html_page("Search", body),
                  extra_headers=[setcookie] if setcookie else None)

    def post_search(self):
        sid, sess, _ = self.session()
        form = self.form_body()
        if not sess or form.get("csrf_token") != sess.get("csrf"):
            return self.send(403, html_page("403", "<p>CSRF token ไม่ถูกต้อง หรือไม่มี cookie</p>"))
        query = form.get("query", "")
        field = form.get("field", "title")
        hits = [b for b in BOOKS if query.lower() in str(b.get(field, "")).lower()]
        rows = "".join(f"<li>{b['title']} — {b['author']} <code>{b['tag']}</code></li>" for b in hits)
        self.send(200, html_page("ผลการค้นหา", f"""
<p>ค้นหา <code>{field}</code> = <code>{query}</code> (ยาว {len(query)} ตัวอักษร)</p>
<ul>{rows or "<li>ไม่พบ</li>"}</ul>
"""))

    # ---------- upload ----------
    def page_upload_form(self, q):
        self.send(200, html_page("Upload", """
<form method="POST" action="/upload" enctype="multipart/form-data">
  <label>ชื่อ <input name="username"></label><br>
  <input type="file" name="file"><br>
  <button type="submit">อัปโหลด</button>
</form>
"""))

    def post_upload(self):
        ctype = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in ctype:
            return self.send_json(400, {"error": "ต้องเป็น multipart/form-data", "got": ctype})
        boundary = ctype.split("boundary=")[-1].strip().strip('"').encode()
        fields, files = parse_multipart(self.read_body(), boundary)
        self.send_json(200, {
            "content_type": ctype,
            "fields": fields,
            "files": {k: {"filename": v[0], "bytes": v[1]} for k, v in files.items()},
        })

    # ---------- SPA (ต้องใช้ browser ถึงจะเห็น) ----------
    def page_spa(self, q):
        self.send(200, """<!doctype html>
<html lang="th"><head><meta charset="utf-8"><title>SPA Demo</title></head>
<body>
<h1>SPA Demo</h1>
<div id="app">กำลังโหลด...</div>
<script>
  fetch('/api/spa-data')
    .then(r => r.json())
    .then(d => {
      document.getElementById('app').innerHTML =
        '<p id="secret">ความลับที่ curl มองไม่เห็น: ' + d.secret + '</p>';
      document.cookie = 'js_seen=1; path=/';
    });
</script>
</body></html>""")

    def api_spa_data(self, q):
        self.send_json(200, {"secret": "HTML ตัวจริงถูกสร้างโดย JavaScript", "ts": int(time.time())})

    # ---------- PoW CAPTCHA ----------
    def api_challenge(self, q):
        difficulty = int(q.get("difficulty", 50_000))
        difficulty = max(10, min(difficulty, 1_000_000))
        self.send_json(200, make_challenge(difficulty))

    def post_solution(self):
        try:
            data = json.loads(self.read_body() or b"{}")
        except json.JSONDecodeError:
            return self.send_json(400, {"ok": False, "error": "body ไม่ใช่ JSON ที่ถูกต้อง"})

        payload = data.get("captcha")
        if not isinstance(payload, str):
            return self.send_json(400, {
                "ok": False,
                "error": 'ต้องส่ง {"captcha": "<base64 string>"} — ALTCHA ส่ง payload เป็น base64 ไม่ใช่ object',
            })

        ok, reason = verify_payload(payload)
        if not ok:
            return self.send_json(400, {"ok": False, "error": reason})

        token = secrets.token_hex(16)
        SOLVED[token] = time.time() + 300
        self.send_json(200, {"ok": True, "message": "PoW ผ่านแล้ว ใช้ /api/protected ได้ 5 นาที"},
                       extra_headers=[("Set-Cookie", f"pow_token={token}; Path=/; Max-Age=300")])

    def api_protected(self, q):
        token = self.cookies().get("pow_token")
        exp = SOLVED.get(token or "")
        if not exp:
            return self.send_json(403, {"ok": False, "error": "ต้องผ่าน PoW ก่อน (ไม่มี cookie pow_token)"})
        if exp < time.time():
            SOLVED.pop(token, None)
            return self.send_json(403, {"ok": False, "error": "pow_token หมดอายุ ขอ challenge ใหม่"})
        self.send_json(200, {"ok": True, "data": BOOKS, "note": "คุณผ่านด่าน anti-bot แล้ว"})

    # ---------- Authentication แบบต่าง ๆ ----------
    def page_basic_auth(self, q):
        """HTTP Basic auth: user:pass ถูก base64 ใส่มาใน Authorization header"""
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Basic "):
            # 401 + WWW-Authenticate คือสิ่งที่ทำให้ browser เด้ง popup ถาม user/pass
            return self.send(401, html_page("401", "<p>ต้องใส่ Basic auth</p>"),
                             extra_headers=[("WWW-Authenticate", 'Basic realm="Lab"')])
        try:
            decoded = base64.b64decode(auth[6:]).decode("utf-8")
            user, _, password = decoded.partition(":")
        except Exception:
            return self.send(400, html_page("400", "<p>Authorization header เสีย</p>"))

        if USERS.get(user) != password:
            return self.send(401, html_page("401", "<p>user/pass ผิด</p>"),
                             extra_headers=[("WWW-Authenticate", 'Basic realm="Lab"')])

        self.send(200, html_page("Basic auth ผ่าน", f"""
<p>สวัสดี <b>{user}</b></p>
<p>สังเกตว่า base64 <b>ไม่ใช่การเข้ารหัส</b> — ใครดัก traffic ได้ก็ decode กลับได้ทันที
   Basic auth จึงปลอดภัยเฉพาะบน HTTPS เท่านั้น</p>
<pre>{auth}</pre>
"""))

    def api_keyed(self, q):
        """API key: ส่งมาใน header ที่ server กำหนดเอง (ที่นิยมคือ X-API-Key)"""
        key = self.headers.get("X-API-Key") or q.get("api_key")
        if not key:
            return self.send_json(401, {
                "ok": False,
                "error": "ต้องส่ง API key มาใน header X-API-Key (หรือ query ?api_key= ซึ่งไม่แนะนำ)",
                "hint": "ลอง demo-key-123",
            })
        owner = API_KEYS.get(key)
        if not owner:
            return self.send_json(403, {"ok": False, "error": "API key ไม่ถูกต้อง"})
        self.send_json(200, {
            "ok": True,
            "owner": owner,
            "via": "X-API-Key" if self.headers.get("X-API-Key") else "query string",
            "note": "API key เป็นความลับระยะยาว ไม่หมดอายุเอง จึงห้าม commit ลง git",
        })

    def post_token(self):
        """
        แลก username/password เป็น bearer token (คล้าย OAuth2 password grant)
        รับได้ทั้ง JSON และ form-urlencoded เพื่อให้ฝึกทั้งสองแบบ
        """
        ctype = self.headers.get("Content-Type", "")
        body = self.read_body()
        if "application/json" in ctype:
            try:
                data = json.loads(body or b"{}")
            except json.JSONDecodeError:
                return self.send_json(400, {"error": "body ไม่ใช่ JSON"})
        else:
            data = dict(urllib.parse.parse_qsl(body.decode("utf-8")))

        user = data.get("username")
        if USERS.get(user) != data.get("password"):
            return self.send_json(401, {"error": "invalid_grant", "detail": "user/pass ผิด"})

        self.send_json(200, issue_token_pair(user, secrets.token_hex(8)) | {
            "note": "access token อายุ 2 นาที เพื่อให้เห็นว่าหมดอายุแล้วต้อง refresh",
        })

    def post_refresh(self):
        """
        แลก refresh token ใบเก่าเป็นคู่ใหม่ (refresh token rotation)
        ใบเก่าถูกเผาทิ้งทันที และถ้ามีคนเอาใบที่ใช้แล้วมาใช้ซ้ำ
        = สัญญาณว่า token รั่ว -> เพิกถอนทั้ง family
        """
        try:
            data = json.loads(self.read_body() or b"{}")
        except json.JSONDecodeError:
            return self.send_json(400, {"error": "body ไม่ใช่ JSON"})

        token = data.get("refresh_token")
        info = REFRESH.get(token or "")
        if not info:
            return self.send_json(401, {"error": "invalid_grant", "detail": "refresh token ไม่ถูกต้อง"})

        if info["used"]:
            # reuse detection: ใบนี้เคยถูกใช้ไปแล้ว
            family = info["family"]
            revoked = [t for t, v in REFRESH.items() if v["family"] == family]
            for t in revoked:
                REFRESH.pop(t, None)
            for t in [t for t, v in TOKENS.items() if v.get("family") == family]:
                TOKENS.pop(t, None)
            return self.send_json(401, {
                "error": "invalid_grant",
                "detail": f"ตรวจพบการใช้ refresh token ซ้ำ — เพิกถอนทั้ง family แล้ว ({len(revoked)} ใบ) ต้อง login ใหม่",
            })

        if info["exp"] < time.time():
            REFRESH.pop(token, None)
            return self.send_json(401, {"error": "invalid_grant", "detail": "refresh token หมดอายุ ต้อง login ใหม่"})

        info["used"] = True
        self.send_json(200, issue_token_pair(info["user"], info["family"]))

    def current_user(self):
        """คืนชื่อ user จาก Bearer token หรือ None ถ้าไม่มี/ใช้ไม่ได้"""
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        info = TOKENS.get(auth[7:].strip())
        if not info or info["exp"] < time.time():
            return None
        return info["user"]

    def api_me(self, q):
        """endpoint ที่ต้องใช้ Authorization: Bearer <token>"""
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return self.send_json(401, {
                "ok": False,
                "error": "ต้องมี header: Authorization: Bearer <token>",
                "hint": "ขอ token ที่ POST /api/token",
            })
        token = auth[7:].strip()
        info = TOKENS.get(token)
        if not info:
            return self.send_json(401, {"ok": False, "error": "token ไม่ถูกต้อง"})
        if info["exp"] < time.time():
            TOKENS.pop(token, None)
            return self.send_json(401, {"ok": False, "error": "token หมดอายุแล้ว ขอใหม่ที่ POST /api/token"})
        self.send_json(200, {
            "ok": True,
            "user": info["user"],
            "expires_in": round(info["exp"] - time.time()),
        })

    # ---------- บทที่ 24: BOLA / IDOR ----------
    def api_order(self, version, order_id):
        """
        v1 = มีช่องโหว่ BOLA โดยเจตนา (ตรวจแค่ว่า "เป็นใคร" ไม่ตรวจว่า "ของใคร")
        v2 = แก้แล้ว
        ลองเทียบสองอันนี้ด้วย token ของ myuser กับ order ของ otheruser
        """
        user = self.current_user()
        if not user:
            return self.send_json(401, {"error": "unauthorized",
                                        "message": "ต้องมี Authorization: Bearer <token>"})

        order = ORDERS.get(order_id)

        if version == "v1":
            # ❌ ผ่าน authentication แล้วก็ให้เลย - นี่คือ BOLA
            if not order:
                return self.send_json(404, {"error": "not_found"})
            return self.send_json(200, {"data": order, "warning": "endpoint นี้มีช่องโหว่ BOLA"})

        # ✅ v2: ตรวจ "ความเป็นเจ้าของ" ก่อนเสมอ
        # ตอบ 404 เหมือนกันทั้งกรณีไม่มีจริงและกรณีไม่ใช่ของเรา
        # เพื่อไม่ให้ผู้โจมตีไล่เดาได้ว่า id ไหนมีอยู่ (object enumeration)
        if not order or order["owner"] != user:
            return self.send_json(404, {"error": "not_found",
                                        "message": "ไม่พบคำสั่งซื้อนี้"})
        return self.send_json(200, {"data": order})

    # ---------- บทที่ 26: proxy / caching ----------
    def api_echo_ip(self, q):
        """แสดงว่า server เห็น IP อะไร - ต่างกันยังไงเมื่ออยู่หลัง reverse proxy"""
        self.send_json(200, {
            "remote_addr": self.client_address[0],
            "x_forwarded_for": self.headers.get("X-Forwarded-For"),
            "x_real_ip": self.headers.get("X-Real-IP"),
            "forwarded": self.headers.get("Forwarded"),
            "note": ("ถ้าอยู่หลัง proxy remote_addr จะเป็น IP ของ proxy ทุกคน "
                     "ต้องอ่านจาก X-Forwarded-For แทน แต่ห้ามเชื่อทั้งก้อน (ดูบทที่ 26)"),
        })

    def api_cached(self, q):
        """ETag + 304 Not Modified - ประหยัด bandwidth ของผู้ใช้มือถือ"""
        body = json.dumps({"items": BOOKS}, ensure_ascii=False, indent=2).encode()
        etag = '"' + hashlib.sha256(body).hexdigest()[:16] + '"'

        # client ส่ง ETag ที่มีอยู่กลับมาถามว่า "ยังใช้ได้ไหม"
        if self.headers.get("If-None-Match") == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", "max-age=60")
            self.end_headers()
            return

        self.send(200, body, "application/json; charset=utf-8",
                  [("ETag", etag), ("Cache-Control", "max-age=60")])

    # ---------- บทที่ 29: Server-Sent Events ----------
    def api_stream(self, q):
        """SSE - ส่งข้อมูลทีละชิ้นโดยไม่ปิดการเชื่อมต่อ ลองด้วย curl -N"""
        count = max(1, min(int(q.get("count", 5)), 20))

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")   # ไม่มี Content-Length
        self.end_headers()

        try:
            for i in range(1, count + 1):
                data = json.dumps({"seq": i, "ts": int(time.time())}, ensure_ascii=False)
                # รูปแบบ SSE: "event:" (ไม่บังคับ) + "data:" + บรรทัดว่างคั่นแต่ละก้อน
                self.wfile.write(f"event: tick\ndata: {data}\n\n".encode())
                self.wfile.flush()
                time.sleep(0.5)
            self.wfile.write(b"event: done\ndata: {}\n\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass    # client ปิดไปก่อน - เรื่องปกติของ stream

    # ---------- บทที่ 25: SSRF (มีช่องโหว่โดยเจตนา) ----------
    def api_fetch(self, q):
        """
        ⚠️ endpoint นี้ "มีช่องโหว่ SSRF โดยเจตนา" เพื่อใช้ทำแบบฝึกหัดบทที่ 25
        ปิดไว้เป็นค่าเริ่มต้น เปิดด้วย LAB_ENABLE_SSRF=1
        ห้ามเขียนโค้ดแบบนี้ในของจริง - วิธีแก้อยู่ในบทที่ 25
        """
        if not ENABLE_SSRF_LAB:
            return self.send_json(403, {
                "error": "disabled",
                "message": "endpoint นี้มีช่องโหว่โดยเจตนา เปิดด้วย LAB_ENABLE_SSRF=1 python3 lab/server.py",
            })

        url = q.get("url")
        if not url:
            return self.send_json(400, {"error": "missing_url", "hint": "?url=http://..."})

        # ❌ ไม่มีการตรวจอะไรเลย - นี่แหละคือ SSRF
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                preview = r.read(200).decode("utf-8", "replace")
                return self.send_json(200, {"status": r.status, "preview": preview})
        except Exception as e:
            return self.send_json(502, {"error": "fetch_failed", "detail": str(e)})


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Lab server: http://{HOST}:{PORT}")
    print("กด Ctrl-C เพื่อหยุด\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
