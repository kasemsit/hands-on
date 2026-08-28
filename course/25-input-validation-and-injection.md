# บทที่ 25 · Input validation, Injection, SSRF และการอัปโหลดไฟล์

> หลักการเดียวที่ครอบคลุมทั้งบท:
> **แยก "ข้อมูล" ออกจาก "คำสั่ง" ให้ขาดจากกัน**
> ช่องโหว่ injection ทุกชนิดเกิดจากการที่สองอย่างนี้ปนกัน

## 25.1 Input validation — allowlist เสมอ {#s25-1}

```python
# ❌ blocklist — ห้ามสิ่งที่รู้ว่าไม่ดี (มีทางเลี่ยงเสมอ)
if "DROP" in query or "--" in query:
    reject()

# ✅ allowlist — อนุญาตเฉพาะสิ่งที่รู้ว่าดี
if not re.fullmatch(r"[a-zA-Z0-9_-]{1,50}", username):
    reject()
```

blocklist แพ้เสมอเพราะคุณต้องคิดให้ครบทุกทาง ส่วนผู้โจมตีต้องหาเจอแค่ทางเดียว
(`DROP` vs `dRoP` vs `DR/**/OP` vs URL-encoded vs Unicode homoglyph...)

### validate ที่ขอบ ด้วย schema

```python
from pydantic import BaseModel, Field, EmailStr

class CreateOrder(BaseModel):
    item_id: int = Field(gt=0)
    qty: int = Field(ge=1, le=100)
    note: str = Field(default="", max_length=500)
    email: EmailStr

    model_config = {"extra": "forbid"}   # ← field แปลกปลอม = error
```

`extra: forbid` สำคัญมาก — ดูหัว[ข้อ 25.6](#s25-6) (mass assignment)

**ตรวจอะไรบ้าง:** ชนิด, ช่วงค่า, ความยาว, รูปแบบ, ค่าที่อนุญาต (enum),
**และขนาดของ request ทั้งก้อน** (กัน payload ขนาด 1 GB มาถล่ม)

> ⚠️ **validate ที่ client ไม่ใช่ security** — มันคือ UX ที่ดี (บอกผู้ใช้เร็ว)
> แต่ผู้โจมตีใช้ curl ข้ามได้หมด **ต้อง validate ที่ server เสมอ**

## 25.2 SQL Injection {#s25-2}

```python
# ❌ ต่อ string — ช่องโหว่คลาสสิกที่ยังเจอทุกปี
cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")
```

ใส่ `name = ' OR '1'='1` แล้วคำสั่งกลายเป็น:

```sql
SELECT * FROM users WHERE name = '' OR '1'='1'    -- ได้ทุกแถว
```

```python
# ✅ parameterized query — DB แยก "คำสั่ง" กับ "ข้อมูล" ให้เอง
cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
```

**พารามิเตอร์ไม่สามารถกลายเป็นคำสั่งได้เลย** ไม่ว่าค่าจะเป็นอะไร นี่คือการแก้ที่ต้นเหตุ
— ไม่ใช่การ "escape" ซึ่งยังพลาดได้

**สิ่งที่ parameterize ไม่ได้: ชื่อตาราง/คอลัมน์** ต้องใช้ allowlist:

```python
SORTABLE = {"id", "created_at", "amount"}          # allowlist
if sort_by not in SORTABLE:
    raise BadRequest()
cursor.execute(f"SELECT * FROM orders ORDER BY {sort_by}")   # ปลอดภัยเพราะผ่าน allowlist
```

**ORM ก็ยังพลาดได้** ถ้าใช้ raw query:

```python
User.objects.raw(f"SELECT * FROM users WHERE name='{name}'")     # ❌ ยังพัง
User.objects.filter(name=name)                                    # ✅
```

## 25.3 Injection ชนิดอื่นที่หลักการเดียวกัน {#s25-3}

| ชนิด | เกิดเมื่อ | แก้ด้วย |
|------|-----------|---------|
| **Command injection** | เอา input ไปต่อใน shell command | ใช้ list argument ไม่ใช่ `shell=True` |
| **NoSQL injection** | MongoDB รับ object ที่มี `$gt` เป็นต้น | ตรวจชนิดข้อมูลว่าเป็น string จริง |
| **LDAP / XPath injection** | ต่อ string ในคิวรี | ใช้ API ที่ parameterize ได้ |
| **Template injection** | เอา input ไปเป็น template | อย่าให้ user คุม template |
| **Log injection** | input มี `\n` ปลอมบรรทัด log ได้ | escape newline ก่อน log |
| **Header injection** | input มี `\r\n` แทรก header ได้ | strip CR/LF ออกจากค่าที่ใส่ใน header |

**Command injection** เป็นตัวที่อันตรายที่สุดและเกี่ยวกับคอร์สนี้โดยตรง
เพราะเราเรียกใช้ `curl` จากโค้ดกันบ่อย:

```python
import subprocess

# ❌ shell=True + string — ใส่ url = "http://x; rm -rf ~" แล้วจบเลย
subprocess.run(f"curl -s {url}", shell=True)

# ✅ ส่งเป็น list — argument ไม่มีทางกลายเป็นคำสั่ง
subprocess.run(["curl", "-s", url], check=True)
```

ใน bash หลักการเดียวกันคือ **ใส่ quote รอบตัวแปรเสมอ** ([บทที่ 20](20-shell-scripting-for-curl.md))

## 25.4 SSRF — ช่องโหว่ที่คนทำ API มักเจอ {#s25-4}

**SSRF (Server-Side Request Forgery)** = หลอกให้ server ของคุณยิง request แทน

เกิดเมื่อ API รับ URL จากผู้ใช้แล้วไปดึงเอง เช่น "ใส่ URL รูปโปรไฟล์",
"import จาก URL", "webhook URL", "ดึง preview ของลิงก์"

**ทำไมอันตรายกว่าที่คิด:** server ของคุณอยู่**ข้างใน**เครือข่าย มันเข้าถึงสิ่งที่
คนนอกเข้าไม่ได้

```
http://169.254.169.254/latest/meta-data/iam/security-credentials/
   → credential ของ AWS (คลาสสิกที่สุด)
http://metadata.google.internal/computeMetadata/v1/
   → GCP metadata
http://localhost:6379/  →  Redis ภายใน
http://10.0.0.5:5432/   →  ฐานข้อมูลภายใน
file:///etc/passwd      →  ไฟล์บนเครื่อง
```

### ลองในlab

```bash
# endpoint นี้มีช่องโหว่โดยเจตนา ต้องเปิดก่อน
fuser -k 8080/tcp; LAB_ENABLE_SSRF=1 python3 lab/server.py &
sleep 1

B=http://127.0.0.1:8080
curl -s "$B/api/fetch?url=http://127.0.0.1:8080/api/books" | jq
curl -s --data-urlencode 'url=file:///etc/hostname' -G "$B/api/fetch" | jq
```

โค้ดที่มีช่องโหว่ (ดู `api_fetch` ใน [lab/server.py](../lab/server.py)):

```python
with urllib.request.urlopen(url, timeout=3) as r:   # ❌ ไม่ตรวจอะไรเลย
```

### วิธีแก้ที่ถูกต้อง

```python
import ipaddress, socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}

def safe_fetch(url: str):
    parsed = urlparse(url)

    # 1. allowlist ของ scheme — ตัด file://, gopher://, dict:// ทิ้ง
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError("scheme ไม่อนุญาต")

    # 2. resolve เป็น IP แล้วตรวจว่าไม่ใช่วงภายใน
    #    ต้องตรวจ "ทุก IP" ที่ชื่อนี้ resolve ได้
    infos = socket.getaddrinfo(parsed.hostname, None)
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast):
            raise ValueError(f"IP ภายในไม่อนุญาต: {ip}")

    # 3. ห้ามตาม redirect เอง — ปลายทางอาจ redirect ไป 169.254.169.254
    # 4. จำกัดเวลาและขนาด
    ...
```

**สี่กับดักที่ทำให้การป้องกันไม่สมบูรณ์:**

1. **DNS rebinding** — ตอนตรวจ domain resolve เป็น IP สาธารณะ แต่ตอนยิงจริง
   resolve เป็น `127.0.0.1` (TTL สั้น ๆ) → ต้อง**ตรวจ IP แล้วยิงไปที่ IP นั้นตรง ๆ**
   ไม่ใช่ resolve ใหม่
2. **Redirect** — ปลายทางตอบ 302 ไป `169.254.169.254` → **ปิด redirect
   หรือตรวจทุก hop**
3. **IPv6 และรูปแบบแปลก ๆ** — `http://[::1]/`, `http://2130706433/`
   (เลขทศนิยมของ 127.0.0.1), `http://0177.0.0.1/` (ฐานแปด)
4. **`localhost` ที่ชี้ที่อื่น** — ตรวจที่ IP หลัง resolve เสมอ ไม่ใช่ที่ชื่อ

**ทางที่ปลอดภัยที่สุด:** ถ้าเป็นไปได้ ให้ผู้ใช้**อัปโหลดไฟล์แทนการให้ URL**
หรือถ้าจำเป็นจริง ให้ยิงผ่าน **egress proxy แยก** ที่มี allowlist ของปลายทาง
และรันในเครือข่ายที่แตะอะไรภายในไม่ได้เลย

> **โยงกับ[บทที่ 13](13-webhooks-and-hmac.md)**: webhook URL ที่ลูกค้าตั้งเองก็คือ SSRF surface
> — ต้องตรวจแบบเดียวกันก่อนยิง

## 25.5 การอัปโหลดไฟล์ {#s25-5}

```bash
curl -F 'file=@evil.php' $B/upload      # จะเกิดอะไรขึ้น?
```

**ห้าอย่างที่ต้องทำ:**

### 1. อย่าเชื่อชื่อไฟล์ที่ส่งมา

```python
# ❌ path traversal — ชื่อไฟล์อาจเป็น "../../etc/cron.d/backdoor"
open(f"/uploads/{filename}", "wb")

# ✅ ตั้งชื่อใหม่เองทั้งหมด
import secrets, os
ext = os.path.splitext(filename)[1].lower()
if ext not in {".jpg", ".png", ".pdf"}:
    raise BadRequest()
safe_name = f"{secrets.token_hex(16)}{ext}"
```

### 2. อย่าเชื่อ Content-Type ที่ client ส่ง

```bash
curl -F 'file=@evil.php;type=image/png' $B/upload    # ปลอมได้ง่าย ๆ
```

ตรวจจาก **magic bytes** ของไฟล์จริง:

```python
SIGNATURES = {b"\xff\xd8\xff": "jpg", b"\x89PNG\r\n\x1a\n": "png", b"%PDF-": "pdf"}
head = content[:8]
kind = next((v for sig, v in SIGNATURES.items() if head.startswith(sig)), None)
if kind is None:
    raise BadRequest("ไม่ใช่ไฟล์ที่รองรับ")
```

### 3. เก็บนอก web root และเสิร์ฟผ่านโค้ด

ถ้าเก็บในโฟลเดอร์ที่ web server เสิร์ฟตรง ๆ ไฟล์ `.php`/`.jsp` ที่อัปโหลดขึ้นไป
อาจถูก**รันเป็นโค้ด** ทางที่ดีกว่า: เก็บใน S3/โฟลเดอร์แยก แล้วเสิร์ฟผ่าน endpoint
ที่ตรวจสิทธิ์ (**BOLA! [บทที่ 24](24-authorization-and-bola.md)**) พร้อม header ที่ปลอดภัย:

```
Content-Type: application/octet-stream       # อย่าเชื่อ type ที่ผู้ใช้ส่ง
Content-Disposition: attachment
X-Content-Type-Options: nosniff              # กันเบราว์เซอร์เดา type เอง
```

### 4. จำกัดขนาดและจำนวน

```
client_max_body_size 10M;      # nginx — ตัดตั้งแต่ชั้น proxy
```

รวมถึงกัน **zip bomb** (ไฟล์ 1 MB แตกออกเป็น 10 GB) ถ้ามีการแตกไฟล์

### 5. สแกนและตัด metadata

รูปถ่ายมี **EXIF ที่มีพิกัด GPS** — ถ้าแสดงต่อสาธารณะ ควรลบทิ้ง
และควรสแกนไวรัส (ClamAV) ถ้าไฟล์จะถูกดาวน์โหลดโดยผู้ใช้คนอื่น

## 25.6 Mass assignment (BOPLA) {#s25-6}

```python
# ❌ รับทุก field ที่ส่งมา
user.update(**request.json)
```

```bash
curl -X PATCH $B/v1/me --json '{"name":"Kasem","role":"admin","credit":999999}'
```

ผู้ใช้เลื่อนขั้นตัวเองเป็น admin ได้ทันที

```python
# ✅ allowlist ของ field ที่แก้ได้
ALLOWED = {"name", "bio", "avatar_url"}
updates = {k: v for k, v in request.json.items() if k in ALLOWED}
user.update(**updates)
```

หรือใช้ schema ที่ `extra: forbid` ([ข้อ 25.1](#s25-1)) ซึ่งจะ **error ทันที**
เมื่อเจอ field แปลกปลอม — ดีกว่าเงียบ ๆ เพราะคุณจะรู้ว่ามีคนพยายาม

**ขาออกก็ต้อง allowlist เหมือนกัน** ([ข้อ 24.8](24-authorization-and-bola.md#s24-8)) — อย่าโยน DB object ออกไปตรง ๆ

## 25.7 เรื่องอื่นที่ควรรู้ {#s25-7}

| ช่องโหว่ | เกี่ยวกับ API คุณไหม | สรุปวิธีกัน |
|----------|---------------------|-------------|
| **XSS** | ถ้ามีหน้าเว็บ/WebView | escape ตอน render, CSP, `HttpOnly` cookie |
| **Path traversal** | ถ้ามีการอ่านไฟล์ตามชื่อ | normalize path แล้วเช็คว่ายังอยู่ในโฟลเดอร์ที่อนุญาต |
| **XXE** | ถ้ารับ XML | ปิด external entity ใน XML parser |
| **Deserialization** | pickle/Java serialize | **อย่า deserialize ข้อมูลจากผู้ใช้** ใช้ JSON |
| **ReDoS** | regex ที่ backtrack หนัก | หลีกเลี่ยง nested quantifier, ใส่ timeout |
| **Zip bomb** | ถ้าแตกไฟล์ | จำกัดขนาดหลังแตก |
| **Prototype pollution** | Node.js | ระวัง `__proto__` ใน object ที่มาจาก JSON |

**ReDoS** เป็นตัวที่คนคาดไม่ถึงและเกี่ยวกับ validation โดยตรง:

```python
re.match(r"^(a+)+$", "a" * 30 + "!")     # ใช้เวลาเป็นวินาที/นาที
```

ถ้า regex นั้นใช้ validate input ผู้โจมตีทำให้ CPU เต็มได้ด้วย request ไม่กี่ตัว

## 25.8 Dependency และ secret {#s25-8}

ช่องโหว่ที่คุณไม่ได้เขียนเองก็ทำให้ระบบพังได้:

```bash
pip-audit                       # Python
npm audit --production          # Node
```

- เปิด **Dependabot** / **Renovate** ใน repo
- ล็อกเวอร์ชัน (`requirements.txt` แบบ pin, `package-lock.json`) และ commit ลง git
- สแกน secret ที่หลุดลง git ด้วย `gitleaks` หรือ `trufflehog`
- ถ้า secret หลุดขึ้น git แล้ว: **หมุน secret ทันที** — การลบ commit ไม่พอ
  เพราะมันถูก clone/index ไปแล้ว

## 25.9 Checklist {#s25-9}

**Input**
- [ ] validate ด้วย schema ที่ขอบของระบบ ใช้ allowlist ไม่ใช่ blocklist
- [ ] `extra: forbid` — ปฏิเสธ field ที่ไม่รู้จัก
- [ ] จำกัดขนาด request ทั้งก้อน
- [ ] validate ที่ server เสมอ ไม่ใช่แค่ที่ client

**Injection**
- [ ] parameterized query ทุกที่ ไม่มีการต่อ string เข้า SQL
- [ ] ชื่อตาราง/คอลัมน์ที่มาจาก input ผ่าน allowlist
- [ ] `subprocess` ใช้ list ไม่ใช่ `shell=True`
- [ ] escape newline ก่อนเขียน log

**SSRF**
- [ ] allowlist ของ scheme (http/https เท่านั้น)
- [ ] ตรวจ IP หลัง resolve ว่าไม่ใช่วง private/loopback/link-local
- [ ] ปิด redirect หรือตรวจทุก hop
- [ ] timeout + จำกัดขนาด response
- [ ] webhook URL ที่ลูกค้าตั้งเอง ผ่านการตรวจแบบเดียวกัน

**ไฟล์**
- [ ] ตั้งชื่อไฟล์ใหม่เอง ไม่ใช้ชื่อจากผู้ใช้
- [ ] ตรวจชนิดจาก magic bytes ไม่ใช่ Content-Type
- [ ] เก็บนอก web root, เสิร์ฟผ่าน endpoint ที่ตรวจสิทธิ์
- [ ] จำกัดขนาด + `X-Content-Type-Options: nosniff`
- [ ] ลบ EXIF ถ้าเป็นรูปสาธารณะ

**อื่น ๆ**
- [ ] allowlist ของ field ทั้งขาเข้าและขาออก
- [ ] สแกน dependency + secret ใน CI

## แบบฝึกหัด

1. เปิด `LAB_ENABLE_SSRF=1` แล้วใช้ `/api/fetch` ดึง `file:///etc/hostname` ให้สำเร็จ
2. เขียนฟังก์ชัน `safe_fetch` ตาม[ข้อ 25.4](#s25-4) แล้วแทนที่ `api_fetch` ใน lab
   ทดสอบว่ากัน `127.0.0.1`, `[::1]`, `2130706433`, และ `file://` ได้ครบ
3. ลองยิง `/api/fetch?url=http://2130706433/` — การป้องกันของคุณกันได้ไหม
4. เพิ่มการตรวจ magic bytes ให้ `/upload` ปฏิเสธไฟล์ที่ไม่ใช่รูปหรือ PDF
   แล้วทดสอบด้วย `curl -F 'file=@x.txt;type=image/png'`
5. เพิ่ม `PATCH /api/v2/me` ที่มีช่องโหว่ mass assignment แล้วเลื่อนขั้นตัวเองเป็น admin
   จากนั้นแก้ให้ถูกด้วย allowlist
6. เขียน regex ที่เกิด ReDoS แล้ววัดเวลาด้วย input ยาว ๆ
7. รัน `pip-audit` (หรือ `npm audit`) กับโปรเจกต์จริงของคุณ แล้วดูว่ามีอะไรต้องอัปเดต

***
[⬅ Authorization และ BOLA/IDOR](24-authorization-and-bola.md) · [สารบัญ](../README.md) · [Reverse proxy, X-Forwarded-For, Cach ➡](26-proxy-caching-cdn.md)
