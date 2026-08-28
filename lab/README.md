# Lab Server — สนามฝึกบนเครื่องคุณเอง

server เล็ก ๆ ที่จำลองพฤติกรรมของเว็บจริง ไว้ให้ยิง curl ทดลองได้เต็มที่
โดยไม่ต้องไปรบกวนเว็บของคนอื่น

**ใช้ Python stdlib ล้วน ไม่ต้อง `pip install` อะไรเลย**

## เริ่มใช้

```bash
python3 lab/server.py
```

```
Lab server: http://127.0.0.1:8080
กด Ctrl-C เพื่อหยุด
```

เปิด <http://127.0.0.1:8080> ในเบราว์เซอร์เพื่อดูรายการ endpoint ทั้งหมด

> state ทั้งหมด (session, token, PoW) เก็บใน memory — **รีสตาร์ท = ล้างหมด**
> ถ้าเจอ 401/403 แปลก ๆ ให้เช็คก่อนว่าเพิ่งรีสตาร์ท server ไปหรือเปล่า

**บัญชีทดสอบ:** `myuser` / `mypass` และ `otheruser` / `otherpass`
(ต้องมีสองบัญชีเพื่อทดสอบ BOLA ในบทที่ 24) — **API key:** `demo-key-123`

## Endpoint ทั้งหมด

### พื้นฐาน (บทที่ 1-2)

| Endpoint | ทำอะไร | ลอง |
|----------|--------|-----|
| `GET /` | หน้าแรก รายการ endpoint | `curl -s localhost:8080/` |
| `GET /headers` | สะท้อน header ที่คุณส่งมาเป็น JSON | `curl -s -A 'MyApp/1.0' localhost:8080/headers \| jq .headers` |
| `GET /slow` | ตอบช้า 3 วินาที | `curl --max-time 1 localhost:8080/slow` |
| `GET /api/books` | JSON API `?tag=` กรองได้ | `curl -s 'localhost:8080/api/books?tag=curl' \| jq` |

### Form, Cookie, CSRF, Redirect (บทที่ 3-5)

| Endpoint | ทำอะไร |
|----------|--------|
| `GET /login` | form + hidden `csrf_token` + ตั้ง cookie `sid` |
| `POST /login` | ตรวจ CSRF + user/pass → **302** ไป `/dashboard` |
| `GET /dashboard` | ต้อง login ก่อน ไม่งั้น 401 |
| `GET /search` | form ค้นหา (มี CSRF) |
| `POST /search` | urlencoded — ลองคำที่มี space และภาษาไทย |
| `GET /upload` | form อัปโหลด |
| `POST /upload` | multipart — บอกกลับว่าได้ field/ไฟล์อะไรมา |

```bash
bash lab/solutions/login-flow.sh        # ดู flow เต็ม
```

### Authentication (บทที่ 9-11)

| Endpoint | ต้องมีอะไร | ลอง |
|----------|-----------|-----|
| `GET /basic` | Basic auth | `curl -u myuser:mypass localhost:8080/basic` |
| `GET /api/keyed` | `X-API-Key` | `curl -H 'X-API-Key: demo-key-123' localhost:8080/api/keyed` |
| `POST /api/token` | user/pass | `curl --json '{"username":"myuser","password":"mypass"}' localhost:8080/api/token` |
| `GET /api/me` | `Authorization: Bearer` | access token อายุ **120 วินาที** |
| `POST /api/refresh` | `{"refresh_token": "..."}` | หมุนใบใหม่ + ตรวจจับการใช้ซ้ำ |

```bash
bash lab/solutions/auth-flow.sh         # ดูทั้ง 4 วิธี + reuse detection
```

### CAPTCHA แบบ Proof of Work (บทที่ 16)

| Endpoint | ทำอะไร |
|----------|--------|
| `GET /api/challenge` | ให้โจทย์ PoW (`?difficulty=` ปรับความยากได้ 10 - 1,000,000) |
| `POST /api/solution` | รับ `{"captcha": "<base64>"}` — สำเร็จแล้วได้ cookie `pow_token` (5 นาที) |
| `GET /api/protected` | เข้าได้เมื่อมี `pow_token` เท่านั้น |

```bash
bash lab/solutions/pow-flow.sh          # ทำครบทั้ง 4 ขั้น

# ดูว่าใน payload มีอะไร
curl -s localhost:8080/api/challenge | python3 lab/solve_pow.py | base64 -d | jq
```

**ทำตามรูปแบบของ ALTCHA v1 จริง** — payload เป็น base64 ของ JSON ไม่ใช่ JSON object

### Authorization, proxy, cache, stream (บทที่ 24-29)

| Endpoint | ทำอะไร |
|----------|--------|
| `GET /api/v1/orders/{id}` | **มีช่องโหว่ BOLA โดยเจตนา** — token ใครก็ดู order คนอื่นได้ |
| `GET /api/v2/orders/{id}` | เวอร์ชันที่ตรวจความเป็นเจ้าของแล้ว (ตอบ 404 ไม่ใช่ 403) |
| `GET /api/echo-ip` | เทียบ `remote_addr` กับ `X-Forwarded-For` |
| `GET /api/cached` | ETag + 304 Not Modified |
| `GET /api/stream` | Server-Sent Events (`?count=` ปรับจำนวนได้) |
| `GET /api/fetch?url=` | **SSRF โดยเจตนา** — ต้องเปิดด้วย `LAB_ENABLE_SSRF=1` |

```bash
# BOLA: myuser ดู order ของ otheruser ได้ไหม
A=$(curl -s --json '{"username":"myuser","password":"mypass"}' localhost:8080/api/token | jq -r .access_token)
curl -s -H "Authorization: Bearer $A" localhost:8080/api/v1/orders/1002 | jq   # รั่ว!
curl -s -H "Authorization: Bearer $A" localhost:8080/api/v2/orders/1002 | jq   # 404

# ETag: ครั้งที่สองได้ 0 bytes
ET=$(curl -s -D - -o /dev/null localhost:8080/api/cached | grep -i '^etag' | tr -d '\r' | awk '{print $2}')
curl -s -o /dev/null -w 'HTTP %{http_code} ได้ %{size_download} bytes\n' -H "If-None-Match: $ET" localhost:8080/api/cached

# SSE
curl -N 'localhost:8080/api/stream?count=3'
```

> ⚠️ `/api/v1/orders/` และ `/api/fetch` **มีช่องโหว่โดยเจตนา** เพื่อใช้ทำแบบฝึกหัด
> ห้ามลอกโค้ดสองส่วนนี้ไปใช้จริง — วิธีที่ถูกอยู่ในบทที่ 24 และ 25

### หน้าที่ต้องใช้ browser (บทที่ 17-18)

| Endpoint | ทำอะไร |
|----------|--------|
| `GET /spa` | HTML ว่างเปล่า เนื้อหาสร้างด้วย JS — **curl มองไม่เห็น** |
| `GET /api/spa-data` | ข้อมูลที่ JS ไปดึงมา |

```bash
curl -s localhost:8080/spa | grep app      # เห็นแค่ "กำลังโหลด..."
python3 lab/solutions/playwright_cookies.py --demo
```

## ไฟล์ในโฟลเดอร์นี้

| ไฟล์ | คืออะไร |
|------|---------|
| `server.py` | lab server |
| `solve_pow.py` | ตัวแก้โจทย์ PoW (อ่าน challenge จาก stdin → พิมพ์ payload base64) |
| `db_demo.py` | บทที่ 27 — วัดผลจริงของ N+1 / index / `SELECT *` ด้วย sqlite |
| `gpu/vram_calc.py` | บทที่ 47 — คำนวณ VRAM / KV cache ว่าเสิร์ฟได้กี่คน |
| `gpu/batching_demo.py` | บทที่ 48 — วัดผลจริงของ batching และ dtype |
| `gpu/ldpreload_quota/` | บทที่ 49 — **HAMi ดัก CUDA API ยังไง** (รันได้แม้ไม่มี GPU) |
| `solutions/login-flow.sh` | เฉลยบท 3-5 — CSRF + cookie + redirect |
| `solutions/auth-flow.sh` | เฉลยบท 9-11 — Basic / API key / Bearer / rotation |
| `solutions/pow-flow.sh` | เฉลยบท 16 — PoW ครบ flow |
| `solutions/playwright_cookies.py` | เฉลยบท 18 — cookie จาก Playwright → curl (มีโหมด `--demo`) |

## จุดที่ตั้งใจทำไม่ครบ (เป็นแบบฝึกหัด)

lab นี้**จงใจ**ละเว้นบางอย่างไว้ให้คุณเติมเอง:

- ❌ **PoW ยังใช้ payload ซ้ำได้** — ยิง payload เดิมสองครั้งก็ผ่านทั้งสองครั้ง
  (แบบฝึกหัด 16.5 — ข้อนี้สำคัญมาก ถ้าไม่แก้ PoW แทบไม่มีความหมาย)
- ❌ ไม่มี rate limiting (แบบฝึกหัด 12.2)
- ❌ ไม่มี pagination (แบบฝึกหัด 12.1)
- ❌ ไม่มี `Idempotency-Key` (แบบฝึกหัด 12.3)
- ❌ ไม่มี `/api/logout` และ `/api/logout-all` (แบบฝึกหัด 11.3-11.4)
- ❌ ไม่มี honeypot field (แบบฝึกหัด 15.1)
- ❌ ไม่มี webhook endpoint (แบบฝึกหัด 13.1)
- ❌ ไม่มี `X-Request-ID` และ structured log (แบบฝึกหัด 12.4, 28.1-28.2)
- ❌ ไม่มี `/health/live` และ `/health/ready` (แบบฝึกหัด 28.4)
- ❌ SSE ยังไม่มี `id:` และ heartbeat (แบบฝึกหัด 29.2-29.3)
- ⚠️ `/api/v1/orders/` มีช่องโหว่ BOLA **โดยเจตนา** (เทียบกับ v2 — บทที่ 24)
- ⚠️ `/api/fetch` มีช่องโหว่ SSRF **โดยเจตนา** (แบบฝึกหัด 25.2)
- ⚠️ `/api/keyed` ตอบ 403 เมื่อ key ผิด ซึ่งควรเป็น 401 (แบบฝึกหัด 9.5)
- ⚠️ password เก็บเป็น plain text ใน `USERS` — **ของจริงต้องใช้ Argon2/bcrypt** (บทที่ 11.8)

## แก้ปัญหา

| อาการ | แก้ |
|-------|-----|
| `Address already in use` | มี server ค้างอยู่ — `fuser -k 8080/tcp` |
| `Connection refused` | ยังไม่ได้เปิด server |
| ได้ 401/403 ที่ไม่ควรเจอ | เพิ่งรีสตาร์ท server → session หายหมด ต้อง login ใหม่ |
| อยากเปลี่ยน port | แก้ `PORT` ที่ต้นไฟล์ `server.py` |
| `--json` ใช้ไม่ได้ | curl เก่ากว่า 7.82 → ใช้ `-H 'Content-Type: application/json' -d` แทน |

## ⚠️ ข้อควรระวัง

**server นี้ไม่ปลอดภัยโดยเจตนา** — เขียนให้อ่านง่ายเพื่อการเรียนรู้ ไม่ใช่เพื่อ production

- password เก็บเป็น plain text
- ผูกกับ `127.0.0.1` เท่านั้น **อย่าเปลี่ยนเป็น `0.0.0.0`** แล้วเปิดออกอินเทอร์เน็ต
- ไม่มี HTTPS, ไม่มี rate limit, ไม่มี input validation ที่จริงจัง

***
[⬅ เรื่องพวกนี้เขาสอนกันในวิชาไหน](../course/23-where-to-learn-more.md) · [สารบัญ](../README.md)
