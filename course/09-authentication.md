# บทที่ 9 · Authentication — Basic, API key, Bearer

> **Authentication** = คุณเป็นใคร (ยืนยันตัวตน)
> **Authorization** = คุณทำอะไรได้บ้าง (สิทธิ์)
> สองคำนี้ต่างกัน แต่ header ที่ใช้ดันชื่อ `Authorization` — เป็นความสับสนที่ติดมาตั้งแต่ปี 1996

## 9.1 ภาพรวม: 4 วิธีที่เจอบ่อย {#s9-1}

| วิธี | ส่งยังไง | เหมาะกับ | ปัญหา |
|------|----------|----------|-------|
| **Basic** | `Authorization: Basic base64(u:p)` | เครื่องมือภายใน, ทดสอบ | ส่ง password ทุก request |
| **API key** | `X-API-Key: xxx` | server-to-server, งาน batch | ไม่หมดอายุ ผูกกับ "แอป" ไม่ใช่ "คน" |
| **Bearer token** | `Authorization: Bearer xxx` | **mobile app**, SPA | ต้องจัดการอายุ/refresh |
| **Session cookie** | `Cookie: sid=xxx` | เว็บที่ render ฝั่ง server | ต้องกัน CSRF, ไม่เหมาะกับ native app |

**คำตอบสั้น ๆ สำหรับ mobile API: ใช้ Bearer token** — รายละเอียดการออกแบบอยู่ใน[บทที่ 11](11-mobile-api-auth-design.md)

## 9.2 HTTP Basic Authentication {#s9-2}

```bash
curl -u myuser:mypass http://127.0.0.1:8080/basic
```

curl แปลงให้เป็น:

```
Authorization: Basic bXl1c2VyOm15cGFzcw==
```

ซึ่งก็คือ `base64("myuser:mypass")` — **ไม่ใช่การเข้ารหัส** decode กลับได้ใน 1 วินาที:

```bash
echo 'bXl1c2VyOm15cGFzcw==' | base64 -d     # myuser:mypass
```

ลองดูว่า server ตอบอะไรเมื่อไม่ส่ง credential:

```bash
curl -i http://127.0.0.1:8080/basic
```

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Basic realm="Lab"
```

`WWW-Authenticate` คือสิ่งที่ทำให้เบราว์เซอร์เด้ง popup ถาม user/pass

**ข้อควรระวัง:**

- ใช้ได้เฉพาะบน HTTPS เท่านั้น
- ส่ง password ไปทุก request → ยิ่งส่งบ่อยยิ่งมีโอกาสรั่ว
- `-u user:pass` ใน command line จะติดใน `ps` และ history
  ใช้ `-u user` เฉย ๆ curl จะถามรหัสแบบไม่แสดงบนจอ
- ไม่มีทาง logout ที่ดี (เบราว์เซอร์จำ credential ไว้)
- **ไม่เหมาะกับ mobile app** เพราะต้องเก็บ password ไว้ในเครื่อง

## 9.3 API key {#s9-3}

```bash
curl -H 'X-API-Key: demo-key-123' http://127.0.0.1:8080/api/keyed | jq
```

API key คือ "รหัสลับตัวยาว" ที่ผูกกับบัญชี/แอปหนึ่ง ๆ

**ส่งที่ไหนดี:**

| ตำแหน่ง | ตัวอย่าง | ความเห็น |
|---------|----------|----------|
| custom header | `X-API-Key: xxx` | ✅ ที่นิยมที่สุด |
| `Authorization` | `Authorization: ApiKey xxx` | ✅ ก็ดี เป็นมาตรฐานกว่า |
| query string | `?api_key=xxx` | ❌ **หลีกเลี่ยง** |

**ทำไม query string แย่**: มันติดใน access log ของ server, ใน proxy log,
ใน `Referer` header ที่ส่งไปเว็บอื่น, และในประวัติเบราว์เซอร์
lab server รองรับทั้งสองแบบเพื่อให้เห็นความต่าง แต่ตอบกลับมาว่ามาทางไหน

```bash
curl -s 'http://127.0.0.1:8080/api/keyed?api_key=demo-key-123' | jq .via
```

**ข้อควรระวังที่สำคัญที่สุด: ห้ามฝัง API key ใน mobile app**

APK/IPA ถูกแกะได้ง่ายมาก (`unzip` + `strings` ก็เห็นแล้ว) key ที่ฝังในแอป
= key สาธารณะ ถ้าจำเป็นต้องเรียก third-party API ที่ต้องใช้ key
ให้ **proxy ผ่าน backend ของคุณ** อย่าให้แอปถือ key ตรง ๆ

### หลักปฏิบัติสำหรับ API key ที่คุณออกให้ลูกค้า

- ยาวพอ (32+ ตัวอักษรสุ่ม) สร้างด้วย CSPRNG (`secrets.token_urlsafe(32)`)
- ใส่ prefix บอกชนิด: `sk_live_...`, `sk_test_...` — ช่วยให้ scanner ตรวจจับได้เวลาหลุดขึ้น GitHub
- **เก็บเป็น hash ในฐานข้อมูล** เหมือน password (เก็บ prefix 8 ตัวแรกไว้แสดงในหน้า UI)
- ให้ผู้ใช้สร้างได้หลายใบ + revoke ทีละใบ + เห็นวันใช้ล่าสุด
- มี scope จำกัดสิทธิ์ (read-only / write)
- รองรับการหมุน: สร้างใบใหม่ → เปลี่ยนใช้ → ลบใบเก่า โดยไม่ต้อง downtime

## 9.4 Bearer token {#s9-4}

```bash
curl -H 'Authorization: Bearer eyJhbGci...' http://127.0.0.1:8080/api/me
```

"Bearer" แปลว่า **ผู้ถือ** — ใครถือ token ใบนี้ก็ใช้ได้ ไม่ต้องพิสูจน์อะไรเพิ่ม
เหมือนตั๋วหนัง ทำให้ token หายเมื่อไรคือปัญหาทันที (จึงต้องมีอายุสั้น)

### ขั้นตอนเต็ม

```bash
B=http://127.0.0.1:8080

# 1. แลก username/password เป็น token
RESP=$(curl -s --json '{"username":"myuser","password":"mypass"}' $B/api/token)
echo "$RESP" | jq

# 2. ใช้ access token
A=$(echo "$RESP" | jq -r .access_token)
curl -s -H "Authorization: Bearer $A" $B/api/me | jq

# 3. ไม่มี token → 401
curl -s $B/api/me | jq
```

โครงสร้างที่ตอบกลับมาเป็นมาตรฐาน OAuth 2.0:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "Bearer",
  "expires_in": 120
}
```

`expires_in` เป็น**วินาที** และเป็น "อีกกี่วินาทีจะหมด" ไม่ใช่เวลาสัมบูรณ์
— ทำแบบนี้เพราะนาฬิกาของ client อาจไม่ตรง

## 9.5 Token แบบ opaque vs JWT {#s9-5}

| | Opaque token | JWT |
|---|-------------|-----|
| หน้าตา | สุ่มมั่ว `a7f3k9...` | `eyJhbGc.eyJzdWI.SflKx` |
| server รู้ได้ยังไงว่าใคร | เปิดดูในฐานข้อมูล | ถอดรหัสจากตัว token เอง |
| ต้องแตะ DB ทุก request | ใช่ | ไม่ |
| revoke ทันที | ✅ ลบจาก DB จบ | ❌ ยาก (ดู[บทที่ 10](10-jwt-deep-dive.md)) |
| ขนาด | เล็ก | ใหญ่กว่า |

lab server ใช้ opaque token (เก็บใน dict `TOKENS`) เพราะเข้าใจง่ายกว่า
JWT อยู่ในบทถัดไป

**คำแนะนำ:** ถ้าคุณมี server เดียว/ฐานข้อมูลเดียว **opaque token ง่ายกว่าและปลอดภัยกว่า**
JWT คุ้มเมื่อคุณมีหลาย service ที่ต้อง verify เองโดยไม่อยากคุยกับ auth server ทุกครั้ง

## 9.6 401 vs 403 ในบริบท auth (ย้ำอีกครั้ง เพราะสำคัญมาก) {#s9-6}

```
401 = "token ไหน? / token นี้ใช้ไม่ได้แล้ว"   → client ควร refresh หรือ login ใหม่
403 = "รู้ว่าคุณคือใคร แต่คุณไม่มีสิทธิ์"       → client ไม่ควร refresh
```

ถ้าคุณตอบ 401 ในกรณีที่ควรเป็น 403 mobile app จะวน refresh → ล้มเหลว → refresh ไม่รู้จบ
เปลืองแบตผู้ใช้และถล่ม server ตัวเอง

**ทดลองดู:**

```bash
curl -s -o /dev/null -w '%{http_code}\n' $B/api/me                              # 401 ไม่มี token
curl -s -o /dev/null -w '%{http_code}\n' -H 'Authorization: Bearer มั่ว' $B/api/me  # 401 token ผิด
curl -s -o /dev/null -w '%{http_code}\n' -H 'X-API-Key: ผิด' $B/api/keyed          # 403 key ผิด*
```

\* จริง ๆ กรณี key ผิดควรเป็น 401 ด้วย lab ตั้งเป็น 403 ไว้ให้เห็นความต่าง —
ลองแก้ [lab/server.py](../lab/server.py) ให้ถูกดูเป็นแบบฝึกหัด

## 9.7 ตารางเปรียบเทียบสรุป {#s9-7}

| เกณฑ์ | Basic | API key | Bearer + refresh | Session cookie |
|-------|-------|---------|------------------|----------------|
| เหมาะกับ mobile | ❌ | ⚠️ เฉพาะ backend | ✅ | ⚠️ เฉพาะ WebView |
| เหมาะกับ server-to-server | ⚠️ | ✅ | ✅ (client_credentials) | ❌ |
| revoke ได้ | ❌ | ✅ | ✅ | ✅ |
| หมดอายุเอง | ❌ | ❌ | ✅ | ✅ |
| ต้องกัน CSRF | ไม่ | ไม่ | ไม่ | **ใช่** |
| ความยากในการทำ | ง่ายสุด | ง่าย | ปานกลาง | ปานกลาง |

> **สรุปสำหรับงานคุณ:** mobile app → Bearer token + refresh token
> ถ้ามี partner integration ด้วย → เพิ่ม API key สำหรับ server-to-server

## แบบฝึกหัด

1. เรียก `/basic` ทั้งแบบมีและไม่มี `-u` เทียบ status code และ header ที่ได้
2. decode ค่า `Authorization: Basic ...` ที่ curl ส่ง (ดูด้วย `-v`) กลับเป็นข้อความ
3. ส่ง API key ผ่าน query string กับผ่าน header เทียบผลลัพธ์ แล้วอธิบายว่าทำไม
   query string อันตรายกว่า
4. ขอ token แล้วรอ 2 นาที ยิง `/api/me` ใหม่ — ได้อะไร แล้ว client ควรทำอย่างไรต่อ
5. แก้ `api_keyed` ใน [lab/server.py](../lab/server.py) ให้ตอบ 401 แทน 403 เมื่อ key ผิด
   แล้วอธิบายว่าทำไมถึงถูกต้องกว่า
6. เขียนสคริปต์ที่ลองทั้ง 3 วิธี (เฉลย: `lab/solutions/auth-flow.sh`)

***
[⬅ JSON API และ jq](08-json-api-and-jq.md) · [สารบัญ](../README.md) · [JWT เจาะลึก ➡](10-jwt-deep-dive.md)
