# บทที่ 10 · JWT เจาะลึก

> JWT เป็นเทคโนโลยีที่ถูกใช้ผิดบ่อยที่สุดเรื่องหนึ่งใน web security
> บทนี้จะสอนทั้งวิธีใช้ และวิธี**ไม่**ใช้

## 10.1 JWT คืออะไร {#s10-1}

JSON Web Token = JSON ที่ถูก encode + **เซ็นชื่อกำกับ** เพื่อให้แก้ไม่ได้โดยไม่ถูกจับได้

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjMiLCJleHAiOjE3MDB9.dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk
└──────────── header ────────────┘ └────────── payload ──────────┘ └────────── signature ──────────┘
```

สามส่วนคั่นด้วยจุด แต่ละส่วนเป็น **base64url** (ไม่ใช่ base64 ธรรมดา — ดู[บทที่ 6](06-encoding-and-charset.md))

**decode ด้วยมือ:**

```bash
JWT='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjMiLCJleHAiOjE3MDB9.xxx'

# header
echo "$JWT" | cut -d. -f1 | base64 -d 2>/dev/null | jq
# payload
echo "$JWT" | cut -d. -f2 | base64 -d 2>/dev/null | jq
```

ถ้า `base64 -d` บ่นเรื่อง padding ให้เติมเอง:

```bash
decode_jwt_part() {
    local s="$1"
    s="${s//-/+}"; s="${s//_//}"           # base64url → base64
    while (( ${#s} % 4 )); do s="${s}="; done   # เติม padding
    echo "$s" | base64 -d
}
decode_jwt_part "$(cut -d. -f2 <<< "$JWT")" | jq
```

## 10.2 ⚠️ ข้อที่สำคัญที่สุดของทั้งบท {#s10-2}

> **JWT ไม่ได้เข้ารหัส payload — ใครก็อ่านได้**

signature ป้องกันการ**แก้ไข** ไม่ได้ป้องกันการ**อ่าน**

```bash
# ใครก็ทำแบบนี้ได้ ไม่ต้องมีกุญแจอะไรเลย
echo "$JWT" | cut -d. -f2 | base64 -d | jq
```

**ห้ามใส่สิ่งเหล่านี้ใน JWT payload เด็ดขาด:**
password, เลขบัตรประชาชน, เลขบัตรเครดิต, ข้อมูลสุขภาพ, API key อื่น ๆ,
หรืออะไรก็ตามที่คุณไม่อยากให้ผู้ใช้เห็นเกี่ยวกับตัวเอง

(ถ้าต้องการเข้ารหัสจริง ๆ มีมาตรฐานชื่อ JWE แต่ซับซ้อนกว่ามากและไม่ค่อยจำเป็น)

## 10.3 Header {#s10-3}

```json
{"alg": "HS256", "typ": "JWT", "kid": "key-2026-01"}
```

| field | ความหมาย |
|-------|----------|
| `alg` | อัลกอริทึมที่ใช้เซ็น |
| `typ` | ชนิด (ปกติ `JWT`) |
| `kid` | key id — บอกว่าใช้กุญแจใบไหนเซ็น (สำคัญตอนหมุนกุญแจ) |

**อัลกอริทึมที่ควรใช้:**

| alg | ชนิด | ใช้เมื่อไร |
|-----|------|-----------|
| `HS256` | symmetric (กุญแจเดียว) | ✅ service เดียว ออกและ verify เอง |
| `RS256` / `ES256` | asymmetric (private/public) | ✅ หลาย service, ให้คนอื่น verify ได้ |
| `none` | ไม่มี signature | ❌ **ห้ามใช้ ห้ามยอมรับ** |

**HS256 vs RS256 ตัดสินใจยังไง:**
ถ้าคนที่ verify token = คนที่ออก token → HS256 พอ (เร็วกว่า ง่ายกว่า)
ถ้ามี service อื่นต้อง verify ด้วย → RS256 เพราะแจก public key ได้โดยไม่ให้อำนาจออก token

## 10.4 Payload — claims มาตรฐาน {#s10-4}

```json
{
  "iss": "https://api.myapp.com",
  "sub": "user_12345",
  "aud": "myapp-mobile",
  "exp": 1735689600,
  "iat": 1735689300,
  "nbf": 1735689300,
  "jti": "tok_01H8X...",
  "scope": "read write",
  "role": "user"
}
```

| claim | เต็ม | ต้อง verify ไหม |
|-------|------|-----------------|
| `iss` | issuer — ใครออก | ✅ ต้องตรงกับที่คุณคาด |
| `sub` | subject — token นี้แทนใคร | ใช้เป็น user id |
| `aud` | audience — ออกให้ใครใช้ | ✅ กันเอา token ของระบบอื่นมาใช้ |
| `exp` | expiration | ✅ **สำคัญที่สุด** |
| `iat` | issued at | ใช้ตรวจว่าเก่าเกินไปไหม |
| `nbf` | not before | ✅ ถ้ามี |
| `jti` | JWT ID | ใช้ทำ blacklist / กัน replay |

`exp`, `iat`, `nbf` เป็น **Unix timestamp หน่วยวินาที** (ไม่ใช่มิลลิวินาที — พลาดกันบ่อย)

## 10.5 การ verify ที่ถูกต้อง (7 ข้อ) {#s10-5}

server **ต้อง**ทำครบทุกข้อ:

1. ✅ แยก 3 ส่วนได้ถูกต้อง
2. ✅ **`alg` เป็นค่าที่คุณกำหนดไว้ล่วงหน้า** — ห้ามเชื่อค่าใน header
3. ✅ signature ถูกต้องเมื่อตรวจด้วยกุญแจของคุณ
4. ✅ `exp` ยังไม่ถึง (เผื่อ clock skew ได้ ±60 วินาที)
5. ✅ `nbf` ผ่านมาแล้ว (ถ้ามี)
6. ✅ `iss` ตรงกับที่คาด
7. ✅ `aud` ตรงกับ service นี้

**ใช้ library อย่าเขียนเอง** — Python: `pyjwt` / `python-jose`, Node: `jose`

```python
import jwt   # pyjwt

payload = jwt.decode(
    token,
    key=PUBLIC_KEY,
    algorithms=["RS256"],          # ← ระบุเสมอ! ห้ามอ่านจาก header
    audience="myapp-mobile",
    issuer="https://api.myapp.com",
    leeway=60,                     # เผื่อนาฬิกาคลาด
)
```

## 10.6 ช่องโหว่คลาสสิก 4 แบบ {#s10-6}

### 1. `alg: none`

โจมตี: เปลี่ยน header เป็น `{"alg":"none"}` ตัด signature ทิ้ง แล้วแก้ payload ตามใจ
library เก่าบางตัวยอมรับ → กลายเป็น admin ได้ทันที

ป้องกัน: ระบุ `algorithms=[...]` ตอน verify เสมอ

### 2. สับ RS256 → HS256 (algorithm confusion)

โจมตี: เอา **public key** (ซึ่งเปิดเผย) มาใช้เป็น **secret ของ HMAC**
ถ้าโค้ดคุณเลือกอัลกอริทึมตาม `alg` ในตัว token → ผู้โจมตีเซ็น token เองได้

ป้องกัน: ข้อเดียวกัน — hard-code อัลกอริทึมที่ยอมรับ

### 3. secret อ่อน

`HS256` กับ secret ว่า `"secret"` หรือ `"changeme"` → brute force แตกในไม่กี่วินาที
(มีเครื่องมือสำเร็จรูปทำเรื่องนี้)

ป้องกัน: secret สุ่ม 32 byte ขึ้นไป เก็บใน secret manager ไม่ commit ลง git

### 4. ไม่ตรวจ `exp`

พบบ่อยกว่าที่คิด เพราะบางคน `decode` แบบ `verify=False` เพื่อ "ดูข้อมูล"
แล้วเผลอใช้ผลนั้นตัดสินใจ

## 10.7 ปัญหาใหญ่ที่สุดของ JWT: revoke ไม่ได้ {#s10-7}

JWT ที่เซ็นแล้ว **ใช้ได้จนกว่าจะหมดอายุ** ไม่ว่าจะเกิดอะไรขึ้น

```
ผู้ใช้กด "ออกจากระบบทุกอุปกรณ์"  →  JWT ที่ออกไปแล้วยังใช้ได้ต่อ
ตรวจพบว่าบัญชีถูกแฮ็ก           →  JWT ที่ขโมยไปยังใช้ได้ต่อ
ลดสิทธิ์ผู้ใช้จาก admin เป็น user  →  JWT ใบเก่ายังบอกว่าเป็น admin
```

**ทางแก้ที่ใช้กันจริง:**

| วิธี | ทำยังไง | ข้อเสีย |
|------|---------|---------|
| **อายุสั้นมาก** | access token 5-15 นาที | ยังมีช่องว่างเท่าอายุ token |
| **Blacklist ด้วย `jti`** | เก็บ jti ที่ถูกเพิกถอนใน Redis | ต้องแตะ Redis ทุก request (แล้วจะใช้ JWT ทำไม?) |
| **Token version** | เก็บ `tv` ใน JWT เทียบกับใน DB | ต้องแตะ DB (เหมือนกัน) |
| **ใช้ opaque token ไปเลย** | เก็บ token ใน DB/Redis ตรง ๆ | ต้องแตะ DB — แต่ก็ตรงไปตรงมา |

> **ความเห็นที่ตรงไปตรงมา:** ถ้าคุณมี backend เดียวและมี Redis/DB อยู่แล้ว
> **opaque token ตอบโจทย์ดีกว่า JWT** สำหรับ mobile app ทั่วไป
> เพราะ revoke ได้ทันที ขนาดเล็กกว่า และไม่มีช่องโหว่ทั้ง 4 ข้อข้างบน
>
> เลือก JWT เมื่อคุณ**มีเหตุผลชัดเจน** เช่น มี microservice หลายตัวที่ต้อง verify
> โดยไม่อยากให้ทุกตัวยิงมาถาม auth service

lab server จึงใช้ opaque token โดยตั้งใจ

## 10.8 ถ้าเลือกใช้ JWT — สูตรที่แนะนำ {#s10-8}

```
access token   = JWT, อายุ 10-15 นาที, เก็บใน memory ของแอป
refresh token  = opaque (สุ่ม), อายุ 30-90 วัน, เก็บใน secure storage, revoke ได้
```

ได้ข้อดีทั้งสองทาง: request ปกติไม่ต้องแตะ DB (JWT), และยัง revoke session ได้ (refresh opaque)
รายละเอียดการทำ refresh อยู่ในบทถัดไป

## 10.9 เครื่องมือ {#s10-9}

```bash
# ดู JWT ด้วย python (ไม่ verify - แค่ดู)
python3 -c "
import base64, json, sys
h, p, s = sys.argv[1].split('.')
for name, part in (('header', h), ('payload', p)):
    part += '=' * (-len(part) % 4)
    print(name, json.dumps(json.loads(base64.urlsafe_b64decode(part)), indent=2, ensure_ascii=False))
" "$JWT"
```

> ⚠️ **อย่าเอา JWT ของ production ไปวางบนเว็บ jwt.io หรือเว็บ decode ออนไลน์ใด ๆ**
> คุณกำลังส่ง credential ที่ใช้งานได้จริงให้เว็บของคนอื่น decode ในเครื่องตัวเองเสมอ

## แบบฝึกหัด

1. สร้าง JWT ปลอมขึ้นมาเองด้วย python (ใช้ `hmac`) แล้ว decode ดู 3 ส่วน
2. เขียนฟังก์ชัน bash ที่รับ JWT แล้วพิมพ์ payload ออกมาเป็น JSON สวย ๆ
3. ตอบตัวเอง: ถ้าคุณเก็บ `"role": "admin"` ใน JWT แล้ววันหนึ่งลดสิทธิ์ผู้ใช้
   จะเกิดอะไรขึ้นในช่วง 15 นาทีถัดไป
4. เปรียบเทียบ: ระบบของคุณต้องรองรับ "logout ทุกอุปกรณ์" — JWT ล้วนทำได้ไหม
   ต้องเพิ่มอะไร
5. อ่านโค้ด `post_token` และ `api_me` ใน [lab/server.py](../lab/server.py)
   แล้วอธิบายว่าทำไม opaque token ถึง revoke ได้ทันที

***
[⬅ Authentication](09-authentication.md) · [สารบัญ](../README.md) · [ออกแบบ Authentication ให้ Mobile API ➡](11-mobile-api-auth-design.md)
