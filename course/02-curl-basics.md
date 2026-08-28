# บทที่ 2 · curl พื้นฐาน

> curl มี option มากกว่า 250 ตัว แต่คุณใช้จริงประมาณ 20 ตัว บทนี้คือ 20 ตัวนั้น

## 2.1 รูปแบบคำสั่ง {#s2-1}

```bash
curl [options] <URL>
```

**ใส่ URL ใน single quote เสมอ** เพราะ `&`, `?`, `*` มีความหมายพิเศษใน shell

```bash
curl 'http://127.0.0.1:8080/api/books?tag=curl'     # ถูก
curl http://127.0.0.1:8080/api/books?tag=curl       # & จะทำให้ shell พัง
```

## 2.2 Option ที่ใช้ 90% ของเวลา {#s2-2}

| Option | ยาว | ทำอะไร |
|--------|-----|--------|
| `-s` | `--silent` | ไม่แสดง progress bar (แต่ก็ซ่อน error ด้วย) |
| `-S` | `--show-error` | แสดง error แม้ใช้ `-s` — **ใช้คู่กับ `-s` เสมอ** |
| `-f` | `--fail` | ถ้า HTTP ≥ 400 ให้ exit code ไม่ใช่ 0 |
| `-L` | `--location` | ตาม redirect |
| `-i` | `--include` | แสดง response header ด้วย |
| `-I` | `--head` | ขอแค่ header (ใช้ HEAD) |
| `-v` | `--verbose` | แสดงทั้ง request และ response header |
| `-o f` | `--output f` | เขียนลงไฟล์ |
| `-O` | `--remote-name` | เขียนลงไฟล์ชื่อเดียวกับใน URL |
| `-H` | `--header` | เพิ่ม header |
| `-d` | `--data` | ส่ง body แบบ urlencoded (POST อัตโนมัติ) |
| `-F` | `--form` | ส่ง body แบบ multipart |
| `-X` | `--request` | บังคับ method |
| `-c` | `--cookie-jar` | **เขียน** cookie ลงไฟล์ |
| `-b` | `--cookie` | **อ่าน** cookie จากไฟล์/string |
| `-u` | `--user` | Basic auth |
| `-A` | `--user-agent` | ตั้ง User-Agent |
| `-e` | `--referer` | ตั้ง Referer |
| `-k` | `--insecure` | ข้ามการตรวจ TLS cert (**อันตราย** ดู[บทที่ 7](07-tls-https.md)) |
| `--max-time` | | timeout ทั้งคำสั่ง (วินาที) |
| `--retry` | | ลองใหม่กี่ครั้งถ้าล้มเหลว |

### ชุด flag ที่ควรจำเป็นคำเดียว

```bash
curl -fsSL 'URL'
```

อ่านว่า: **f**ail ถ้า error, **s**ilent, แต่ **S**how error, และตาม **L**ocation
นี่คือชุดมาตรฐานสำหรับใช้ใน script

`-sL` ที่เห็นบ่อยในตัวอย่างตามอินเทอร์เน็ตก็คือ `-s -L` — curl รวม flag ตัวเดียวติดกันได้

> **ทำไมต้อง `-f`**: ถ้าไม่ใส่ เวลา server ตอบ 500 พร้อม HTML หน้า error
> curl จะถือว่า "สำเร็จ" (exit 0) แล้ว script ของคุณจะทำงานต่อกับข้อมูลขยะ

## 2.3 อ่าน `-v` ให้เป็น {#s2-3}

```bash
curl -v 'http://127.0.0.1:8080/api/books?tag=curl'
```

```
*   Trying 127.0.0.1:8080...            ← curl เล่าให้ฟัง (ไม่ใช่ข้อมูลบนสาย)
* Connected to 127.0.0.1 port 8080
> GET /api/books?tag=curl HTTP/1.1      ← ขาออก
> Host: 127.0.0.1:8080
> User-Agent: curl/8.5.0
> Accept: */*
>
< HTTP/1.1 200 OK                       ← ขากลับ
< Content-Type: application/json; charset=utf-8
< Content-Length: 180
<
{"count": 1, ...}                       ← body
```

จำสามสัญลักษณ์: `*` = curl พูด, `>` = ส่งไป, `<` = รับมา

ถ้าอยากเห็นละเอียดกว่านั้น (ทุก byte จริง ๆ รวม body ขาออก):

```bash
curl --trace-ascii trace.txt 'http://127.0.0.1:8080/api/books'
```

## 2.4 `-w` — ดึงตัวเลขออกมาใช้ต่อ {#s2-4}

`--write-out` ให้คุณพิมพ์ค่าที่ curl รู้ออกมาได้ เหมาะกับ script และการวัดความเร็ว

```bash
curl -s -o /dev/null -w 'status=%{http_code} time=%{time_total}s size=%{size_download}\n' \
     http://127.0.0.1:8080/
```

ตัวแปรที่ใช้บ่อย:

| ตัวแปร | ความหมาย |
|--------|----------|
| `%{http_code}` | status code |
| `%{url_effective}` | URL สุดท้ายหลังตาม redirect |
| `%{time_total}` | เวลารวม |
| `%{time_namelookup}` | เวลา DNS |
| `%{time_connect}` | เวลาต่อ TCP |
| `%{time_appconnect}` | เวลาจบ TLS handshake |
| `%{num_redirects}` | ตาม redirect ไปกี่ครั้ง |
| `%{size_download}` | ขนาด body |

**เทคนิควัดว่าช้าตรงไหน:**

```bash
curl -s -o /dev/null -w 'dns=%{time_namelookup} tcp=%{time_connect} tls=%{time_appconnect} total=%{time_total}\n' \
     https://example.com
```

ถ้า `tls` โตกว่าชาวบ้าน = ปัญหาที่ handshake, ถ้า `total` ห่างจาก `tls` มาก = server คิดนาน

## 2.5 Timeout และ retry {#s2-5}

```bash
curl --max-time 10 --connect-timeout 3 --retry 3 --retry-delay 2 'URL'
```

- `--connect-timeout` — รอต่อสายนานสุดกี่วิ
- `--max-time` — ทั้งคำสั่งนานสุดกี่วิ (กันค้างตลอดกาล)
- `--retry N` — ลองใหม่ N ครั้งเมื่อเจอ error ที่น่าจะหายเอง (5xx, timeout)
- `--retry-all-errors` — ลองใหม่แม้กับ error ที่ปกติไม่ retry

ลองกับ endpoint ที่ตอบช้า 3 วินาที:

```bash
curl --max-time 1 http://127.0.0.1:8080/slow    # จะ timeout
curl --max-time 5 http://127.0.0.1:8080/slow    # จะผ่าน
```

> ⚠️ **อย่า retry method ที่ไม่ idempotent แบบสุ่มสี่สุ่มห้า** — `--retry` กับ POST
> "สร้างคำสั่งซื้อ" อาจได้ออเดอร์ซ้ำ เรื่องนี้อธิบายเต็มใน[บทที่ 12](12-api-design-practices.md) (idempotency key)

## 2.6 exit code {#s2-6}

```bash
curl -fsS http://127.0.0.1:8080/dashboard; echo "exit=$?"
```

| code | ความหมาย |
|------|----------|
| 0 | สำเร็จ |
| 6 | หา host ไม่เจอ (DNS) |
| 7 | ต่อไม่ติด (server ไม่เปิด / port ผิด) |
| 22 | HTTP ≥ 400 (เฉพาะเมื่อใช้ `-f`) |
| 28 | timeout |
| 35 | TLS handshake พัง |
| 60 | ตรวจ certificate ไม่ผ่าน |

ใน script ใช้ตรวจได้ตรง ๆ:

```bash
if ! curl -fsS "$URL" -o out.json; then
    echo "ยิงไม่สำเร็จ (exit $?)" >&2
    exit 1
fi
```

## 2.7 ไฟล์ `.curlrc` และการซ่อนความลับ {#s2-7}

**อย่าใส่ token ใน command line** เพราะคนอื่นบนเครื่องเดียวกันเห็นได้ผ่าน `ps aux`
และมันจะติดไปใน shell history ด้วย

วิธีที่ถูกต้อง:

```bash
# แบบที่ 1: อ่านจาก environment variable
curl -H "Authorization: Bearer $TOKEN" 'URL'

# แบบที่ 2: เก็บ header ไว้ในไฟล์ (curl 7.55+)
echo "Authorization: Bearer abc123" > /tmp/h.txt
chmod 600 /tmp/h.txt
curl -H @/tmp/h.txt 'URL'

# แบบที่ 3: อ่าน body จาก stdin
echo '{"a":1}' | curl -d @- 'URL'
```

`-d @file` = อ่าน body จากไฟล์, `-d @-` = อ่านจาก stdin

## 2.8 แปลง curl ↔ ภาษาอื่น {#s2-8}

- **จาก DevTools มาเป็น curl**: คลิกขวาที่ request → Copy → Copy as cURL ([บทที่ 14](14-devtools-to-curl.md))
- **จาก curl ไปเป็นโค้ด**: <https://curlconverter.com> แปลงเป็น Python/JS/Go ได้
- **`--libcurl out.c`**: ให้ curl เขียนโค้ด C ที่เทียบเท่าคำสั่งนั้นออกมา

## แบบฝึกหัด

1. ยิง `/api/books` แล้วแสดงเฉพาะ status code กับเวลาที่ใช้ ด้วย `-w`
2. เปรียบเทียบ exit code ของสองคำสั่งนี้ แล้วอธิบายว่าทำไมต่างกัน
   ```bash
   curl -s http://127.0.0.1:8080/dashboard > /dev/null; echo $?
   curl -fsS http://127.0.0.1:8080/dashboard > /dev/null; echo $?
   ```
3. ทำให้ `/slow` timeout ด้วย `--max-time` แล้วดูว่า exit code เป็นเท่าไร
4. ใช้ `-v` ยิง `/api/books` แล้วนับว่า curl ส่ง header ไปกี่ตัวโดยที่คุณไม่ได้สั่ง
5. ปิด lab server แล้วยิงใหม่ — exit code คืออะไร ต่างจากข้อ 3 อย่างไร

***
[⬅ HTTP พื้นฐาน](01-http-basics.md) · [สารบัญ](../README.md) · [HTML form → curl ➡](03-html-forms.md)
