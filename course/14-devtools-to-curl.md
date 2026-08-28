# บทที่ 14 · DevTools → curl

> ทักษะที่มีค่าที่สุดในคอร์สนี้ — และสำคัญกว่าการอ่านหนังสือเสียอีก
> เพราะมันทำให้คุณเห็นว่าเว็บจริง ๆ คุยกันอย่างไร ไม่ใช่แค่ทฤษฎี

## 14.1 เปิด Network tab {#s14-1}

`F12` → แท็บ **Network** แล้ว **โหลดหน้าใหม่** (ถ้าไม่โหลดใหม่จะไม่เห็นอะไร)

ตั้งค่าที่ควรเปิดไว้ตลอด:

| ตั้งค่า | ทำไม |
|---------|------|
| ☑ **Preserve log** | ไม่ให้ log หายเวลา redirect หรือเปลี่ยนหน้า — **สำคัญที่สุด** |
| ☑ **Disable cache** | ให้เห็น request จริงทุกครั้ง ไม่ใช่ 304 |
| Filter: **Fetch/XHR** | ตัด CSS/รูป/font ออก เหลือแต่ API call |
| ☑ Big request rows | เห็น URL เต็ม อ่านง่ายขึ้น |

## 14.2 อ่าน request ทีละแท็บ {#s14-2}

คลิกที่ request หนึ่ง จะเห็น:

| แท็บ | ดูอะไร | เอาไปทำอะไรใน curl |
|------|--------|---------------------|
| **Headers → General** | Request URL, Method, Status | URL + `-X` |
| **Headers → Request Headers** | header ทั้งหมดที่ส่งไป | `-H`, `-b`, `-A` |
| **Headers → Response Headers** | `Set-Cookie`, `Location` | เข้าใจว่าอะไรถูกตั้ง |
| **Payload / Request** | body ที่ส่ง | `-d` / `--json` / `-F` |
| **Preview / Response** | สิ่งที่ได้กลับมา | ตรวจว่า curl ได้เหมือนกันไหม |
| **Timing** | ช้าตรงไหน | เทียบกับ `-w '%{time_*}'` |
| **Initiator** | โค้ดบรรทัดไหนเป็นคนยิง | **ทองคำ** — พาไปหา logic ต้นทาง |

**Initiator คือแท็บที่คนมองข้ามแต่มีประโยชน์ที่สุด** — คลิกแล้วมันพาไปที่ JS
บรรทัดที่ยิง request นั้น ทำให้เห็นว่าค่าที่ส่งมาจากไหน คำนวณยังไง

## 14.3 Copy as cURL {#s14-3}

คลิกขวาที่ request → **Copy** → **Copy as cURL**

จะได้คำสั่งยาวเหยียดแบบนี้:

```bash
curl 'https://example.com/api/search' \
  -H 'accept: application/json' \
  -H 'accept-language: th-TH,th;q=0.9' \
  -H 'content-type: application/json' \
  -H 'cookie: sid=abc123; _ga=GA1.1.xxx' \
  -H 'sec-ch-ua: "Chromium";v="120"' \
  -H 'sec-fetch-mode: cors' \
  -H 'user-agent: Mozilla/5.0 ...' \
  --data-raw '{"query":"test"}'
```

> ⚠️ **คำสั่งนี้มี cookie/token ของคุณอยู่ข้างใน** — อย่าวางลงใน chat, issue,
> หรือ pastebin โดยไม่ลบออกก่อน ผมเห็นคนทำหลุดบ่อยมาก

### เลือก "Copy as cURL (bash)" บน Windows

ถ้าใช้ Windows Chrome จะให้ตัวเลือก `cmd` กับ `bash` — เลือก **bash**
ไม่งั้นจะได้ `^` แทน `\` ซึ่งใช้ใน WSL/Linux ไม่ได้

## 14.4 ตัดให้เหลือเท่าที่จำเป็น {#s14-4}

คำสั่งที่ copy มามี header เยอะเกินจำเป็นมาก **วิธีหาว่าอันไหนจำเป็นจริง: ตัดทีละอัน**

**ลำดับการตัด (ตัดจากบนลงล่าง):**

1. `sec-ch-ua*`, `sec-fetch-*`, `sec-ch-*` — เบราว์เซอร์ใส่เอง ตัดได้เกือบตลอด
2. `accept-encoding` — ให้ curl จัดการด้วย `--compressed` แทน
3. `accept-language`, `dnt`, `pragma`, `cache-control` — มักไม่จำเป็น
4. `referer`, `origin` — **ระวัง** บาง API เช็ค
5. `user-agent` — บางเว็บเช็ค ลองตัดดู
6. `cookie` — มักจำเป็น
7. `authorization`, `x-csrf-token`, header แปลก ๆ ที่ขึ้นต้นด้วย `x-` — **เกือบแน่นอนว่าจำเป็น**

ตัดแล้วยิงใหม่ ถ้ายังได้ผลเหมือนเดิม = ตัดถูก ถ้าพัง = ใส่กลับ

เป้าหมายคือเหลือคำสั่งสั้น ๆ ที่คุณ**เข้าใจทุกบรรทัด** ไม่ใช่คำสั่ง 30 บรรทัด
ที่ใช้ได้แต่ไม่รู้ว่าทำไม

## 14.5 หา flow ทั้งหมด ไม่ใช่แค่ request เดียว {#s14-5}

ปัญหาที่พบบ่อย: copy request สุดท้ายมาอย่างเดียวแล้วยิง → 403
เพราะมันต้องมี request ก่อนหน้าที่ทำให้ได้ cookie/token มาก่อน

**วิธีทำ:** ทำงานในหน้าเว็บให้ครบ 1 รอบ โดยเปิด Preserve log ไว้
แล้วไล่ดู request ตามลำดับเวลา หาว่า:

```
GET  /page                      → ได้ cookie + csrf token ใน HTML
GET  /captcha/challenge/xxx     → ได้ challenge
POST /captcha/solution/xxx      → ส่งคำตอบ ได้ cookie ผ่านด่าน
POST /search                    → ส่งของจริง
302 → GET /result               → ได้ผลลัพธ์
```

**หลักการค้นหา: "ค่านี้มาจากไหน"**
เจอค่าประหลาดใน request → ค้นหาค่านั้นใน response ของ request ก่อนหน้า
DevTools มีช่อง **Search** (Ctrl+Shift+F) ที่ค้นได้ทุก response พร้อมกัน — ใช้บ่อยมาก

ถ้าค้นไม่เจอในทุก response แปลว่ามัน**ถูกคำนวณในฝั่ง JS** → ไปดูที่แท็บ Initiator
(หรือถ้าคำนวณยากเกินไป ก็ถึงเวลาใช้ Playwright — [บทที่ 17](17-playwright-basics.md))

## 14.6 เครื่องมือช่วยอื่น ๆ {#s14-6}

```bash
# แปลง curl → Python/JS/Go
# https://curlconverter.com  (ทำงานในเบราว์เซอร์ ไม่ส่งข้อมูลออก แต่ควรลบ token ก่อนอยู่ดี)

# curl → โค้ด C
curl --libcurl out.c 'URL'

# ดูว่า curl ส่งอะไรจริง โดยยิงใส่ตัวเอง
curl [options ที่ copy มา] http://127.0.0.1:8080/headers | jq
```

เทคนิคสุดท้ายนี้มีประโยชน์มาก: เอาคำสั่งที่ copy มาแล้ว**เปลี่ยน URL เป็น lab server ของคุณ**
`/headers` จะสะท้อนทุกอย่างกลับมาให้ดูว่าส่งอะไรไปบ้างจริง ๆ

## 14.7 กรณี mobile app ของคุณเอง {#s14-7}

DevTools ใช้ได้กับเบราว์เซอร์เท่านั้น สำหรับ native app ต้องใช้ proxy — [บทที่ 19](19-mitmproxy-mobile-traffic.md)

แต่ถ้าแอปคุณมี WebView อยู่ ใช้ remote debugging ได้:

- **Android**: เปิด `chrome://inspect` บนเดสก์ท็อป ต่อสายเครื่อง แล้วจะเห็น WebView
- **iOS**: Safari → Develop → เลือกอุปกรณ์

## 14.8 ลองกับ lab {#s14-8}

1. เปิด <http://127.0.0.1:8080/login> พร้อม DevTools (Network tab, Preserve log)
2. กรอก `myuser` / `mypass` แล้วกด Login
3. สังเกตว่าจะเห็น **2 request**: `POST /login` (302) และ `GET /dashboard` (200)
4. คลิก `POST /login` → แท็บ Payload → เห็น `csrf_token`, `username`, `password`
5. Copy as cURL แล้วรันใน terminal
6. ตัด header ทิ้งทีละอันจนเหลือน้อยที่สุดที่ยังใช้ได้

จากนั้นลองอันที่ยากขึ้น:

7. เปิด <http://127.0.0.1:8080/spa> ดูว่ามี `GET /api/spa-data` ตามมา
8. ยิง `curl -s http://127.0.0.1:8080/spa` แล้วเทียบกับที่เห็นในเบราว์เซอร์
   — HTML ที่ curl ได้ **ไม่มีเนื้อหา** เพราะมันถูกสร้างด้วย JS
   นี่คือเหตุผลที่ต้องมี[บทที่ 17](17-playwright-basics.md)

## แบบฝึกหัด

1. ทำตาม[ข้อ 14.8](#s14-8) ทั้ง 8 ข้อ
2. เขียนลำดับ request ทั้งหมดของการ login ออกมาเป็นผัง (แบบใน[ข้อ 14.5](#s14-5))
3. ใช้ Ctrl+Shift+F ค้นหาค่า `csrf_token` ที่ถูกส่งไป — เจอมันครั้งแรกใน response ไหน
4. ลองยิง `POST /login` ด้วย csrf token ที่ถูกต้อง แต่**ไม่ส่ง cookie** — ได้อะไร ทำไม
5. ใช้เทคนิคใน[ข้อ 14.6](#s14-6): เอาคำสั่งที่ copy มา เปลี่ยน URL เป็น `/headers`
   แล้วนับว่าเบราว์เซอร์ส่ง header ไปกี่ตัว เทียบกับ curl เปล่า ๆ

***
[⬅ netcat (`nc`)](A1-netcat.md) · [สารบัญ](../README.md) · [CAPTCHA และสถาปัตยกรรม Anti-bot ➡](15-captcha-and-antibot.md)
