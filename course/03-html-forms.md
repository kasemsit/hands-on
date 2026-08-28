# บทที่ 3 · HTML form → curl

> ทักษะหลักของบทนี้: เห็น `<form>` แล้วเขียน `curl` ที่เทียบเท่าได้ทันที

## 3.1 อ่าน `<form>` ให้ออก

```html
<form method="POST" action="/login">
    <input name="username">
    <input name="password" type="password">
    <button type="submit">Login</button>
</form>
```

สี่จุดที่ต้องดู:

| ดูที่ | ได้อะไร | ไปเป็น curl |
|-------|---------|-------------|
| `method` | GET หรือ POST | GET → query string, POST → `-d` |
| `action` | ส่งไปที่ไหน | URL ของ curl |
| `enctype` | body หน้าตายังไง | ไม่มี = urlencoded, `multipart/form-data` = `-F` |
| `name` ของทุก input | ชื่อ field | `-d 'name=value'` |

**สิ่งที่ไม่มี `name` จะไม่ถูกส่ง** — จำข้อนี้ไว้ debug ได้เยอะ

form ข้างบนแปลงเป็น:

```bash
curl -X POST 'http://127.0.0.1:8080/login' \
    -d 'username=myuser' \
    -d 'password=mypass'
```

`-d` หลายครั้ง curl จะเชื่อมด้วย `&` ให้เอง กลายเป็น `username=myuser&password=mypass`

> `-X POST` ใส่ไปก็ได้ ไม่ใส่ก็ได้ — พอมี `-d` curl เปลี่ยนเป็น POST ให้อัตโนมัติอยู่แล้ว
> แต่ **ระวัง**: ถ้าใส่ `-X POST` คู่กับ `-L` แล้วเจอ 302 curl จะ POST ซ้ำไปที่ปลายทาง
> ซึ่งมักไม่ใช่สิ่งที่ต้องการ (ดู[บทที่ 5](05-redirects-and-headers.md))

## 3.2 `-d` vs `--data-urlencode` — จุดที่คนพลาดบ่อยที่สุด

`-d` **ส่งข้อความไปตรง ๆ ไม่ encode ให้**

ถ้าค่าของคุณมี space, `&`, `+`, `=`, `/`, `#` หรือภาษาไทย มันจะพัง:

```bash
# ผิด: & จะถูกตีความว่าเป็นตัวคั่น field
curl -d 'query=cats & dogs' URL       # server เห็น field ชื่อ " dogs" ด้วย!

# ผิด: + ใน urlencoded แปลว่า space
curl -d 'query=1+1' URL                # server เห็น "1 1"

# ถูก: ให้ curl encode ให้
curl --data-urlencode 'query=cats & dogs' URL
```

**กฎง่าย ๆ: ใช้ `--data-urlencode` เป็นค่าเริ่มต้นเสมอ** ยกเว้นตอนที่คุณ encode มาเองแล้ว

### รูปแบบของ `--data-urlencode`

```bash
--data-urlencode 'name=value'    # encode เฉพาะ value  ← ใช้ตัวนี้เกือบตลอด
--data-urlencode 'value'         # encode ทั้งก้อน ไม่มีชื่อ field
--data-urlencode 'name@file'     # อ่าน value จากไฟล์ แล้ว encode
--data-urlencode '=value'        # encode ทั้งก้อน (ไม่มี name)
```

### ทดลองกับ lab

```bash
# 1) ขอ CSRF token กับ cookie (จะอธิบายเต็มในบทที่ 4)
TOKEN=$(curl -s -c /tmp/c.txt http://127.0.0.1:8080/search \
        | grep -oP 'csrf_token" value="\K[a-f0-9]+')

# 2) ค้นด้วยภาษาไทย
curl -s -b /tmp/c.txt -X POST http://127.0.0.1:8080/search \
    -d "csrf_token=$TOKEN" \
    --data-urlencode 'query=หนังสือ' \
    --data-urlencode 'field=tag'
```

หน้าผลลัพธ์จะบอก "ยาว N ตัวอักษร" ให้ดู — ถ้า encode ถูก คำว่า `หนังสือ` จะได้ 7 ตัวอักษร
ถ้าได้ตัวเลขแปลก ๆ แปลว่า encoding เพี้ยน (ดู[บทที่ 6](06-encoding-and-charset.md))

### อยากรู้ว่าส่งอะไรออกไปจริง ๆ

```bash
curl -v --data-urlencode 'query=cats & dogs' http://127.0.0.1:8080/headers 2>&1 | grep -A2 'Content-Length'
```

หรือใช้ `--trace-ascii /dev/stdout` ก็เห็น body ทุก byte

## 3.3 GET form

```html
<form method="GET" action="/api/books">
    <input name="tag">
</form>
```

GET form ไม่มี body — ค่าไปอยู่ใน query string:

```bash
curl -G 'http://127.0.0.1:8080/api/books' --data-urlencode 'tag=curl'
```

`-G` บอก curl ว่า "เอาข้อมูลจาก `-d`/`--data-urlencode` ไปต่อท้าย URL แทนที่จะใส่ใน body"
วิธีนี้ดีกว่าเขียน `?tag=...` เองเพราะได้ encoding ที่ถูกต้องฟรี

## 3.4 multipart/form-data — สำหรับอัปโหลดไฟล์

```html
<form method="POST" action="/upload" enctype="multipart/form-data">
    <input name="username">
    <input type="file" name="file">
</form>
```

```bash
echo "hello" > doc.txt
curl -F 'username=myuser' -F 'file=@doc.txt' http://127.0.0.1:8080/upload
```

ไวยากรณ์ของ `-F`:

```bash
-F 'name=value'                          # field ธรรมดา
-F 'file=@path/to/file'                  # อัปโหลดไฟล์ (ชื่อไฟล์ตามของจริง)
-F 'file=@path;filename=other.pdf'       # เปลี่ยนชื่อที่ส่งไป
-F 'file=@path;type=application/pdf'     # กำหนด Content-Type ของ part
-F 'data=<path'                          # เอา "เนื้อไฟล์" มาเป็น value (ไม่ใช่ไฟล์แนบ)
-F 'json=@d.json;type=application/json'  # ส่ง JSON เป็น part หนึ่ง
```

จำง่าย ๆ: `@` = แนบเป็นไฟล์, `<` = เอาเนื้อหามาเป็นค่า

body ที่ออกไปจริงหน้าตาแบบนี้:

```
------------------------abc123
Content-Disposition: form-data; name="username"

myuser
------------------------abc123
Content-Disposition: form-data; name="file"; filename="doc.txt"
Content-Type: text/plain

hello
------------------------abc123--
```

**ห้ามใช้ `-F` คู่กับ `-d`** — เลือกอย่างใดอย่างหนึ่ง เพราะเป็นคนละ Content-Type

## 3.5 input ชนิดอื่น ๆ

| HTML | ส่งอะไรไป |
|------|-----------|
| `<input type="hidden" name="csrf" value="abc">` | `-d 'csrf=abc'` — **ต้องส่งด้วยเสมอ** |
| `<input type="checkbox" name="agree" value="yes">` | ติ๊ก → `-d 'agree=yes'` / ไม่ติ๊ก → **ไม่ส่งเลย** |
| `<input type="radio" name="plan" value="pro">` | ส่งเฉพาะตัวที่เลือก |
| `<select name="field"><option value="tag">` | `-d 'field=tag'` |
| `<select multiple name="tags">` | `-d 'tags=a' -d 'tags=b'` (ชื่อซ้ำได้) |
| `<textarea name="note">` | `--data-urlencode 'note=...'` |
| `<button name="action" value="delete">` | ส่งเฉพาะปุ่มที่กด |

**จุดที่พลาดบ่อย**: checkbox ที่ไม่ติ๊ก **ไม่ส่งค่าอะไรเลย** ไม่ใช่ส่ง `agree=off`
ดังนั้นการ "ยกเลิกติ๊ก" คือการ *ไม่ใส่* `-d 'agree=...'`

## 3.6 hidden field และ CSRF token

```html
<input type="hidden" name="csrf_token" value="abc123">
```

hidden field ไม่ได้ "ซ่อน" จาก HTTP — มันแค่ไม่แสดงบนหน้าจอ แต่ถูกส่งทุกครั้ง
ถ้าลืมส่ง server จะปฏิเสธ (403)

ปัญหาคือค่ามันเปลี่ยนทุกครั้งที่โหลดหน้า จึงต้องทำสองขั้น:

```bash
# ขั้นที่ 1: โหลดหน้า form เก็บทั้ง cookie และ token
curl -s -c cookies.txt http://127.0.0.1:8080/login -o form.html

# ขั้นที่ 2: ดึง token ออกมา แล้ว submit พร้อม cookie เดิม
TOKEN=$(grep -oP 'name="csrf_token" value="\K[^"]+' form.html)

curl -s -b cookies.txt -c cookies.txt -L \
    -X POST http://127.0.0.1:8080/login \
    -d "csrf_token=$TOKEN" \
    -d 'username=myuser' \
    -d 'password=mypass'
```

**ทำไม token ต้องมากับ cookie ชุดเดียวกัน**: server ผูก token ไว้กับ session
ถ้าเอา token จาก session A ไปใช้กับ cookie ของ session B จะไม่ผ่าน — นี่คือหัวใจของ CSRF protection
(อธิบายเต็มใน[บทที่ 4](04-cookies-sessions.md))

## 3.7 ดึงค่าจาก HTML: grep พอไหม

`grep -oP` ใช้ได้กับ HTML ง่าย ๆ แต่พังทันทีถ้า HTML ซับซ้อน (attribute สลับตำแหน่ง, ขึ้นบรรทัดใหม่)

ทางเลือกที่ทนกว่า:

```bash
# pup (ติดตั้ง: go install github.com/ericchiang/pup@latest)
curl -s URL | pup 'input[name="csrf_token"] attr{value}'

# python + stdlib (ไม่ต้องลงอะไร)
curl -s URL | python3 -c '
import sys, html.parser
class P(html.parser.HTMLParser):
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "input" and d.get("name") == "csrf_token":
            print(d.get("value"))
P().feed(sys.stdin.read())'
```

สำหรับงานจริงจัง ใช้ Python + `beautifulsoup4` หรือ `lxml` ดีกว่าครับ

## แบบฝึกหัด

1. เปิด <http://127.0.0.1:8080/search> ดู HTML (View Source) แล้วเขียน curl ที่เทียบเท่า
   การกดปุ่มค้นหาด้วยคำว่า `Everything curl` (มี space!)
2. ลองใช้ `-d 'query=Everything curl'` แทน `--data-urlencode` ดูว่าผลต่างกันอย่างไร
   (ดูจากจำนวนตัวอักษรที่หน้าผลลัพธ์รายงาน)
3. อัปโหลดไฟล์ไป `/upload` แล้วเปลี่ยนชื่อไฟล์ที่ส่งด้วย `;filename=`
4. ยิง `/upload` ด้วย `-d` แทน `-F` — server ตอบว่าอะไร แล้วทำไม
5. เขียน script ที่ login ให้สำเร็จโดยไม่เปิด browser เลย (เฉลย: `lab/solutions/login-flow.sh`)

***
[⬅ curl พื้นฐาน](02-curl-basics.md) · [สารบัญ](../README.md) · [Cookie และ Session ➡](04-cookies-sessions.md)
