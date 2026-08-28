# บทที่ 8 · JSON API และ jq

> เว็บสมัยใหม่ไม่ค่อยส่ง HTML form กันแล้ว
> มันคุยกันด้วย JSON — และนี่คือสิ่งที่ mobile app ของคุณจะใช้

## 8.1 ส่ง JSON ด้วย curl {#s8-1}

```bash
curl -X POST http://127.0.0.1:8080/api/token \
     -H 'Content-Type: application/json' \
     -d '{"username":"myuser","password":"mypass"}'
```

สามอย่างที่ต้องมี:

1. `-H 'Content-Type: application/json'` — **ไม่ใส่ไม่ได้** เพราะ `-d` จะตั้งเป็น
   `application/x-www-form-urlencoded` ให้อัตโนมัติ แล้ว server จะ parse ไม่ออก
2. body ที่เป็น JSON ถูกต้อง (single quote รอบนอก, double quote ใน JSON)
3. มักต้องมี `-H 'Accept: application/json'` ด้วยเพื่อบอกว่าอยากได้ JSON กลับ

### curl 7.82+ มีทางลัด

```bash
curl --json '{"username":"myuser","password":"mypass"}' URL
```

`--json` = `-d` + `Content-Type: application/json` + `Accept: application/json` ในตัวเดียว

ตรวจว่าเวอร์ชันคุณรองรับไหม: `curl --version`

### อ่าน body จากไฟล์หรือ stdin

```bash
curl --json @payload.json URL
echo '{"a":1}' | curl --json @- URL
```

## 8.2 สร้าง JSON อย่างปลอดภัยด้วย jq {#s8-2}

**อย่าต่อ string เอง** (เหตุผลอยู่ใน[บทที่ 6](06-encoding-and-charset.md)):

```bash
# ❌ พังเมื่อค่ามี " หรือ \ หรือ newline
curl -d "{\"query\":\"$USER_INPUT\"}" URL

# ✅ ให้ jq จัดการ escaping
BODY=$(jq -nc --arg q "$USER_INPUT" '{query: $q}')
curl --json "$BODY" URL
```

รูปแบบที่ใช้บ่อย:

```bash
jq -nc --arg s "text"      '{name: $s}'          # string
jq -nc --argjson n 42      '{count: $n}'         # number/bool/object/array
jq -nc --arg a "x" --arg b "y" '{a:$a, b:$b}'    # หลายตัว
jq -nc --slurpfile d f.json '{data: $d[0]}'      # เอาไฟล์ JSON มาฝัง
```

จำง่าย ๆ: `--arg` = ส่งเป็น string เสมอ, `--argjson` = ส่งเป็น JSON ตามที่เขียน

## 8.3 jq ที่ใช้จริง 90% {#s8-3}

```bash
B=http://127.0.0.1:8080

curl -s $B/api/books | jq .                    # จัดรูปสวย
curl -s $B/api/books | jq -c .                 # บรรทัดเดียว
curl -s $B/api/books | jq '.count'             # ดึง field
curl -s $B/api/books | jq -r '.items[0].title' # -r = ไม่เอา quote ครอบ
curl -s $B/api/books | jq '.items[]'           # กระจาย array ออกมา
curl -s $B/api/books | jq '.items | length'    # นับ
```

### กรอง แปลง เรียง

```bash
# กรองด้วยเงื่อนไข
curl -s $B/api/books | jq '.items[] | select(.tag == "curl")'

# กรองด้วยข้อความบางส่วน
curl -s $B/api/books | jq '.items[] | select(.title | test("curl"; "i"))'

# เลือกเฉพาะบาง field
curl -s $B/api/books | jq '.items[] | {title, author}'

# เปลี่ยนชื่อ field
curl -s $B/api/books | jq '.items[] | {ชื่อ: .title, คนเขียน: .author}'

# map ทั้ง array
curl -s $B/api/books | jq '[.items[].title]'

# เรียง / จัดกลุ่ม / นับ
curl -s $B/api/books | jq '.items | sort_by(.title)'
curl -s $B/api/books | jq '.items | group_by(.tag) | map({tag: .[0].tag, n: length})'
```

### แปลงเป็นตาราง / CSV

```bash
curl -s $B/api/books | jq -r '.items[] | [.id, .title, .tag] | @tsv' | column -t -s $'\t'
curl -s $B/api/books | jq -r '.items[] | [.id, .title] | @csv'
```

### ค่าที่อาจไม่มี

```bash
jq '.items[0].missing'          # → null
jq '.items[0].missing // "ไม่มี"'  # → ใส่ค่าเริ่มต้น
jq '.a.b.c?'                    # → ไม่ error ถ้า path ไม่มี
jq -e '.ok'                     # -e = exit code สะท้อนผล (ใช้ใน if ได้)
```

`jq -e` มีประโยชน์มากใน script:

```bash
if curl -s $B/api/me -H "Authorization: Bearer $T" | jq -e '.ok' > /dev/null; then
    echo "token ยังใช้ได้"
else
    echo "ต้อง refresh"
fi
```

## 8.4 แยก body กับ status code {#s8-4}

ปัญหาคลาสสิก: อยากได้ทั้งเนื้อหาและ status code ในคำสั่งเดียว

```bash
# วิธีที่ 1 — เขียน body ลงไฟล์ ให้ stdout เหลือแค่ status
CODE=$(curl -s -o /tmp/body.json -w '%{http_code}' $B/api/books)
echo "status=$CODE"
jq . /tmp/body.json

# วิธีที่ 2 — ต่อ status ท้าย body แล้วตัดเอา
RESP=$(curl -s -w '\n%{http_code}' $B/api/books)
CODE=$(tail -n1 <<< "$RESP")
BODY=$(sed '$d' <<< "$RESP")
```

วิธีที่ 1 ปลอดภัยกว่าเพราะไม่ยุ่งกับเนื้อหา body เลย

## 8.5 รูปแบบ error ที่ดี {#s8-5}

เวลา API ของคุณตอบ error ให้ตอบเป็น JSON ที่มีโครงสร้างคงที่ **อย่าตอบ HTML**
เพราะ mobile app จะ parse ไม่ได้แล้ว crash

```json
{
  "error": "invalid_grant",
  "message": "รหัสผ่านไม่ถูกต้อง",
  "request_id": "req_01H8XK...",
  "details": [{"field": "password", "issue": "mismatch"}]
}
```

| field | ใครใช้ | หมายเหตุ |
|-------|--------|----------|
| `error` | โค้ด | รหัสคงที่ ภาษาอังกฤษ ไม่เปลี่ยน — ให้ client `switch` ได้ |
| `message` | คน | ข้อความแสดงผล เปลี่ยนได้ แปลภาษาได้ |
| `request_id` | คุณ | ใส่ใน log ด้วย ผู้ใช้แจ้งปัญหามาแล้วตามเจอทันที |
| `details` | โค้ด | ระบุ field ที่ผิด สำหรับ validation |

**หลักการ: `error` สำหรับเครื่องอ่าน, `message` สำหรับคนอ่าน** อย่าให้ client
ตัดสินใจจากข้อความภาษาไทย เพราะวันหนึ่งคุณจะแก้ข้อความแล้วแอปพัง

## 8.6 Content-Type ที่ควรรู้ {#s8-6}

| Content-Type | ใช้เมื่อไร | curl |
|--------------|-----------|------|
| `application/json` | API ทั่วไป | `--json` / `-H` + `-d` |
| `application/x-www-form-urlencoded` | HTML form | `-d` (ค่าเริ่มต้น) |
| `multipart/form-data` | อัปโหลดไฟล์ | `-F` |
| `text/plain` | ข้อความเปล่า | `-H 'Content-Type: text/plain' -d` |
| `application/octet-stream` | binary ดิบ | `--data-binary @file` |
| `text/event-stream` | Server-Sent Events | `-N` (ไม่ buffer) |
| `application/x-ndjson` | JSON บรรทัดละก้อน (stream) | `-N` |

> **`-d` กับ `--data-binary` ต่างกัน**: `-d` ตัด newline ออกจากไฟล์
> ถ้าส่งไฟล์ binary หรือต้องการรักษาทุก byte ต้องใช้ `--data-binary @file`

## 8.7 อ่าน stream (SSE / NDJSON) {#s8-7}

```bash
curl -N -H 'Accept: text/event-stream' $B/api/stream
```

`-N` = ปิด buffer ทำให้เห็นข้อมูลทันทีที่มาถึง แทนที่จะรอจนจบ
ใช้บ่อยเวลา debug API ที่ stream คำตอบทีละชิ้น

## 8.8 ทดลองกับ lab แบบเต็ม flow {#s8-8}

```bash
B=http://127.0.0.1:8080

# ขอ token
TOK=$(curl -s --json '{"username":"myuser","password":"mypass"}' $B/api/token)
echo "$TOK" | jq

# ดึง access token ออกมาใช้
A=$(echo "$TOK" | jq -r .access_token)

# เรียก endpoint ที่ต้อง auth
curl -s -H "Authorization: Bearer $A" $B/api/me | jq
```

(รายละเอียดเรื่อง token อยู่ในบทถัดไป)

## แบบฝึกหัด

1. ดึงเฉพาะ `title` ของหนังสือทุกเล่มออกมาเป็นบรรทัดละชื่อ
2. หาหนังสือที่ `tag` เป็น `curl` แล้วแสดงเป็น TSV (id, title, author)
3. นับว่ามี tag กี่ชนิด และแต่ละชนิดมีกี่เล่ม (คำใบ้: `group_by`)
4. เขียนคำสั่งที่ดึงทั้ง status code และ body ของ `/api/me` โดยไม่ส่ง token
   แล้วแสดงว่า `error` คืออะไร
5. ใช้ `jq -nc --arg` สร้าง JSON ที่มีค่าเป็นข้อความ `เขา "พูด" ว่า\nสวัสดี`
   แล้วดูว่า jq escape ให้อย่างไร
6. เขียน `if` ใน bash ที่เช็คว่า token ยังใช้ได้ไหมด้วย `jq -e`

***
[⬅ TLS และ HTTPS](07-tls-https.md) · [สารบัญ](../README.md) · [Authentication ➡](09-authentication.md)
