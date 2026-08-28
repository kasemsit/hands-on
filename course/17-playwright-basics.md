# บทที่ 17 · Playwright เบื้องต้น

> curl เห็นแค่ HTML ที่ server ส่งมา
> Playwright เห็นสิ่งที่**ผู้ใช้เห็นจริง** หลัง JavaScript ทำงานเสร็จแล้ว

## 17.1 ทำไมต้องมี Playwright — ดูด้วยตาตัวเอง {#s17-1}

lab มีหน้า `/spa` ที่เนื้อหาถูกสร้างด้วย JavaScript ลองเทียบดู:

```bash
curl -s http://127.0.0.1:8080/spa
```

```html
<div id="app">กำลังโหลด...</div>
<script>fetch('/api/spa-data').then(...)</script>
```

**curl เห็นแค่นี้** — ไม่มีเนื้อหาจริงเลย เพราะ curl ไม่รัน JavaScript
แต่เปิดใน browser จะเห็นข้อความ "ความลับที่ curl มองไม่เห็น: ..."

นี่คือสาเหตุที่ต้องมีเครื่องมือที่รัน JS ได้

## 17.2 เมื่อไรใช้อะไร {#s17-2}

| สถานการณ์ | ใช้ |
|-----------|-----|
| API ที่ตอบ JSON ตรง ๆ | **curl** — เร็วกว่า 100 เท่า |
| HTML ที่ server render มาแล้ว | **curl** |
| เนื้อหาสร้างด้วย JS (SPA/React/Vue) | **Playwright** |
| ต้องรัน JS เพื่อคำนวณ token/signature | **Playwright** |
| CAPTCHA ที่ต้องให้ widget ทำงาน | **Playwright** |
| ต้อง login ผ่าน OAuth/SSO หลายขั้น | **Playwright** |
| ยิงซ้ำ ๆ เยอะ ๆ | **curl** (หรือลูกผสม — [บทที่ 18](18-playwright-cookies-to-curl.md)) |

> **หลักการ: ใช้ Playwright เท่าที่จำเป็น แล้วส่งงานที่เหลือให้ curl**
> Playwright เปิด browser จริง กินแรม 100-300 MB ต่อ instance และช้ากว่ามาก
> บทถัดไปสอนวิธีผสมสองอย่างเข้าด้วยกัน

## 17.3 ติดตั้ง {#s17-3}

```bash
pip install playwright
playwright install chromium          # ดาวน์โหลด browser (~150 MB)
playwright install-deps              # ติดตั้ง library ระบบ (Linux, ต้องใช้ sudo)
```

ถ้าไม่อยากลงในระบบหลัก ใช้ venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install playwright
playwright install chromium
```

Node.js ก็ใช้ได้: `npm i -D @playwright/test && npx playwright install chromium`
บทนี้ใช้ Python เพราะเข้ากับ lab

## 17.4 สคริปต์แรก {#s17-4}

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto("http://127.0.0.1:8080/spa")
    page.wait_for_selector("#secret")          # รอให้ JS ทำงานเสร็จ

    print(page.inner_text("#secret"))          # เห็นสิ่งที่ curl ไม่เห็น
    browser.close()
```

`headless=True` = ไม่แสดงหน้าต่าง (เร็วกว่า) — ตอน debug ใช้ `headless=False`
เพื่อดูว่าเกิดอะไรขึ้น และเพิ่ม `slow_mo=500` เพื่อชะลอให้ดูทัน

```python
browser = p.chromium.launch(headless=False, slow_mo=500)
```

## 17.5 Selector {#s17-5}

Playwright แนะนำให้ใช้ locator ที่อ้างอิงสิ่งที่**ผู้ใช้เห็น** เพราะทนต่อการเปลี่ยน HTML:

```python
page.get_by_role("button", name="Login")    # ✅ ดีที่สุด
page.get_by_label("username")               # ✅
page.get_by_text("ค้นหา")                    # ✅
page.get_by_placeholder("เช่น curl")         # ✅
page.get_by_test_id("submit-btn")           # ✅ ถ้าเว็บคุณใส่ data-testid ไว้

page.locator("#app")                        # CSS
page.locator("input[name='username']")      # CSS
page.locator("xpath=//div[@id='app']")      # XPath (ใช้เป็นทางเลือกสุดท้าย)
```

**อย่าใช้ CSS selector ที่ยาวและเปราะ** เช่น `div > div:nth-child(3) > span.a1b2c3`
— class ที่ถูก generate (`.css-1x2y3z`) จะเปลี่ยนทุกครั้งที่ build

## 17.6 รอ — เรื่องที่สำคัญที่สุด {#s17-6}

**อย่าใช้ `time.sleep()`** มันช้าเกินจำเป็นเมื่อเว็บเร็ว และไม่พอเมื่อเว็บช้า

Playwright มี **auto-waiting** อยู่แล้ว: `click()`, `fill()` จะรอให้ element
ปรากฏและกดได้ก่อนโดยอัตโนมัติ

```python
page.wait_for_selector("#result")                    # รอ element
page.wait_for_selector("#loading", state="hidden")   # รอให้หายไป
page.wait_for_load_state("networkidle")              # รอจนเน็ตเงียบ
page.wait_for_url("**/dashboard")                    # รอ URL เปลี่ยน
page.wait_for_function("() => window.dataReady")     # รอเงื่อนไข JS
page.wait_for_timeout(1000)                          # ทางเลือกสุดท้าย
```

**รอ response ของ API โดยเฉพาะ** — มีประโยชน์มากเวลาทำ CAPTCHA:

```python
with page.expect_response("**/api/spa-data") as resp_info:
    page.goto("http://127.0.0.1:8080/spa")

response = resp_info.value
print(response.status, response.json())
```

## 17.7 กรอกฟอร์ม {#s17-7}

```python
page.goto("http://127.0.0.1:8080/login")
page.fill("input[name='username']", "myuser")
page.fill("input[name='password']", "mypass")
page.click("button[type='submit']")
page.wait_for_url("**/dashboard")
print(page.inner_text("body"))
```

**สังเกตว่าไม่ต้องยุ่งกับ CSRF token เลย** — Playwright โหลดหน้าจริง
token กับ cookie จึงถูกส่งไปเองอัตโนมัติเหมือนที่เบราว์เซอร์ทำ
นี่คือข้อได้เปรียบใหญ่ที่สุดของมัน

## 17.8 ดักและแทรกแซง network {#s17-8}

ความสามารถที่ทรงพลังที่สุดของ Playwright:

```python
# ดูทุก request/response
page.on("request",  lambda r: print(">>", r.method, r.url))
page.on("response", lambda r: print("<<", r.status, r.url))

# บล็อกรูป/font ให้เร็วขึ้นมาก
page.route("**/*.{png,jpg,jpeg,gif,woff2,css}", lambda route: route.abort())

# ปลอม response (ทดสอบ error handling)
page.route("**/api/spa-data", lambda route: route.fulfill(
    status=500, json={"error": "server_error"}))

# แก้ request ก่อนส่ง
page.route("**/api/**", lambda route: route.continue_(
    headers={**route.request.headers, "X-Debug": "1"}))
```

`page.route` กับการบล็อกรูปช่วยให้เร็วขึ้น 2-5 เท่าในเว็บที่มีรูปเยอะ

## 17.9 เรียก JavaScript ในหน้า {#s17-9}

```python
title = page.evaluate("() => document.title")
page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")

# เรียกฟังก์ชันของเว็บเอง — มีประโยชน์มากกับ CAPTCHA
result = page.evaluate("""async () => {
    const widget = document.querySelector('altcha-widget');
    return widget ? widget.getAttribute('challengeurl') : null;
}""")
```

**นี่คือทางออกเวลาเจอ logic ที่ reverse-engineer ยาก** — แทนที่จะแกะว่า
เขาคำนวณ signature ยังไง ก็ให้หน้าเว็บคำนวณให้แล้วดึงค่าออกมา

## 17.10 Debug {#s17-10}

```bash
PWDEBUG=1 python3 myscript.py          # เปิด Playwright Inspector
```

```python
page.screenshot(path="shot.png", full_page=True)
page.pause()                            # หยุดให้เล่นใน Inspector
print(page.content())                   # HTML ปัจจุบัน (หลัง JS แล้ว)

# บันทึกทุกอย่างไว้ดูย้อนหลัง
context = browser.new_context(record_video_dir="videos/")
context.tracing.start(screenshots=True, snapshots=True)
# ... ทำงาน ...
context.tracing.stop(path="trace.zip")   # เปิดดูที่ trace.playwright.dev
```

**codegen — บันทึกการกระทำเป็นโค้ดอัตโนมัติ:**

```bash
playwright codegen http://127.0.0.1:8080/login
```

คลิกในเบราว์เซอร์ที่เปิดขึ้นมา แล้วมันจะเขียนโค้ดให้ — วิธีเริ่มต้นที่เร็วที่สุด
(แต่โค้ดที่ได้มักใช้ selector ที่ไม่สวย ควรแก้เอง)

## 17.11 ข้อควรระวัง {#s17-11}

| เรื่อง | รายละเอียด |
|-------|-----------|
| ทรัพยากร | 100-300 MB ต่อ browser — อย่าเปิดพร้อมกันเยอะ |
| ปิดให้ครบ | ใช้ `with` หรือ `try/finally` ไม่งั้น process ค้าง |
| ช้ากว่า curl มาก | 1-3 วินาทีต่อหน้า เทียบกับ 50 มิลลิวินาที |
| ตรวจจับได้ | `navigator.webdriver === true` และร่องรอยอื่น ๆ |
| Docker | ต้องใช้ image ที่มี dependency ครบ (`mcr.microsoft.com/playwright`) |

เรื่อง "ตรวจจับได้": มี library อย่าง `playwright-stealth` ที่พยายามซ่อน
แต่ **ถ้าคุณกำลังทดสอบเว็บของตัวเอง คุณไม่ต้องซ่อนอะไรเลย** — ตั้ง User-Agent
ให้บอกตรง ๆ ว่าเป็น test runner ของคุณจะดีกว่า และช่วยให้แยก traffic ใน log ได้

## แบบฝึกหัด

1. ติดตั้ง Playwright แล้วรันสคริปต์ใน[ข้อ 17.4](#s17-4) ให้เห็นข้อความที่ curl มองไม่เห็น
2. เขียนสคริปต์ที่ login เข้า `/dashboard` แล้วพิมพ์ session id ออกมา
3. ใช้ `page.on("request", ...)` แล้วนับว่าการโหลด `/spa` ยิง request กี่ครั้ง
4. ใช้ `expect_response` ดักผลของ `/api/spa-data` แล้วพิมพ์ JSON ออกมา
5. ใช้ `page.route` บล็อกไม่ให้ `/api/spa-data` ทำงาน แล้วดูว่าหน้าเว็บแสดงอะไร
6. รัน `playwright codegen` แล้วบันทึกขั้นตอน login — เทียบโค้ดที่ได้กับที่คุณเขียนเอง
7. จับเวลา: `curl -s /spa` เทียบกับสคริปต์ Playwright ที่ทำงานเดียวกัน ต่างกันกี่เท่า

***
[⬅ ALTCHA และ Proof of Work](16-altcha-pow.md) · [สารบัญ](../README.md) · [จาก Playwright สู่ curl ➡](18-playwright-cookies-to-curl.md)
