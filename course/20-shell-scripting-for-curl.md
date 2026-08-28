# บทที่ 20 · เขียน bash ให้ปลอดภัยและไม่พังเงียบ ๆ

> สคริปต์ curl ที่ "ดูเหมือนทำงาน" แต่จริง ๆ ล้มเหลวเงียบ ๆ
> เป็นสิ่งที่อันตรายกว่าสคริปต์ที่พังเสียงดัง

## 20.1 สามบรรทัดแรกของทุกสคริปต์

```bash
#!/usr/bin/env bash
set -euo pipefail
```

| flag | ทำอะไร | ป้องกันอะไร |
|------|--------|-------------|
| `-e` | หยุดทันทีเมื่อคำสั่งใดล้มเหลว | ทำงานต่อกับข้อมูลขยะ |
| `-u` | error เมื่อใช้ตัวแปรที่ไม่ได้ตั้งค่า | `rm -rf "$DIR/"` เมื่อ `$DIR` ว่าง |
| `-o pipefail` | pipeline ล้มเหลวถ้าคำสั่งใดใน pipe ล้มเหลว | `curl ... \| jq` ที่ curl พังแต่ jq ตอบ 0 |

**`pipefail` สำคัญมากกับ curl** เพราะ:

```bash
curl -s http://ไม่มีจริง/ | jq .      # ไม่มี pipefail → exit 0 ทั้งที่พัง
```

ถ้าอยากรู้ว่าบรรทัดไหนพัง เพิ่ม trap:

```bash
trap 'echo "ล้มเหลวที่บรรทัด $LINENO" >&2' ERR
```

## 20.2 ใส่ quote เสมอ

```bash
FILE="my file.txt"

rm $FILE      # ❌ ลบ "my" กับ "file.txt" คนละไฟล์
rm "$FILE"    # ✅
```

**กฎ: ใส่ `"` รอบตัวแปรทุกครั้ง** ยกเว้นตอนที่ตั้งใจให้แตกเป็นหลายคำจริง ๆ

```bash
curl -d "username=$USER" "$URL"                # ✅
BODY=$(jq -nc --arg u "$USER" '{username:$u}') # ✅ ดีกว่าอีก
```

ใช้ [shellcheck](https://www.shellcheck.net/) ตรวจ — มันจับเรื่องพวกนี้ได้หมด

```bash
sudo apt install shellcheck
shellcheck lab/solutions/*.sh
```

## 20.3 ไฟล์ชั่วคราวและการเก็บกวาด

```bash
COOKIE_JAR="$(mktemp)"
RESPONSE="$(mktemp)"
trap 'rm -f "$COOKIE_JAR" "$RESPONSE"' EXIT
```

`trap ... EXIT` ทำงานแม้สคริปต์จะจบด้วย error หรือถูก Ctrl-C
— **สำคัญมากเพราะ cookie jar คือ credential** (บทที่ 18)

ถ้าต้องการทั้งโฟลเดอร์:

```bash
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT
```

`mktemp` สร้างไฟล์ด้วยสิทธิ์ `600` อยู่แล้ว ปลอดภัยกว่า `/tmp/myfile.$$`
ซึ่งเดาชื่อได้และมีปัญหา race condition

## 20.4 อย่าใส่ความลับใน command line

```bash
# ❌ คนอื่นบนเครื่องเห็นได้ด้วย ps aux + ติดใน history
curl -H "Authorization: Bearer sk_live_abc123" "$URL"
curl -u admin:hunter2 "$URL"
```

**ทางที่ปลอดภัย:**

```bash
# 1. environment variable
export API_TOKEN='...'                     # จาก .env ที่ chmod 600
curl -H "Authorization: Bearer $API_TOKEN" "$URL"

# 2. ไฟล์ header
umask 077
printf 'Authorization: Bearer %s\n' "$API_TOKEN" > "$HDR"
curl -H @"$HDR" "$URL"

# 3. ให้ curl ถามเอง (ไม่แสดงบนจอ)
curl -u myuser "$URL"

# 4. .netrc
cat > ~/.netrc <<EOF
machine api.example.com login myuser password mypass
EOF
chmod 600 ~/.netrc
curl -n "$URL"

# 5. secret manager
API_TOKEN="$(pass show api/myapp)"
API_TOKEN="$(op read 'op://vault/api/token')"
```

> วิธีที่ 1 ยังเห็นได้ผ่าน `/proc/PID/environ` โดยเจ้าของ process เดียวกัน
> แต่ดีกว่า command line มาก สำหรับความลับระดับสูงใช้วิธี 2 หรือ 5

**ป้องกันความลับหลุดขึ้น git:**

```bash
cat >> .gitignore <<'EOF'
.env
*.cookies
cookies.txt
state.json
*.mitm
EOF
```

## 20.5 ตรวจผลลัพธ์ทุกครั้ง

```bash
# ❌ ไม่รู้เลยว่าสำเร็จไหม
curl -s "$URL" -o out.json

# ✅
if ! curl -fsS "$URL" -o out.json; then
    echo "ยิง $URL ล้มเหลว" >&2
    exit 1
fi

# ✅ แยก status ออกมาตัดสินใจได้ละเอียด
CODE=$(curl -sS -o "$BODY" -w '%{http_code}' "$URL")
case "$CODE" in
    2*)  : ;;                                     # ผ่าน
    401) echo "token หมดอายุ" >&2; exit 2 ;;
    429) echo "โดน rate limit" >&2; exit 3 ;;
    *)   echo "ไม่คาดคิด: $CODE" >&2; cat "$BODY" >&2; exit 1 ;;
esac
```

**ตรวจว่าเป็น JSON จริงก่อน parse** — server ที่พังมักตอบ HTML:

```bash
if ! jq -e . "$BODY" > /dev/null 2>&1; then
    echo "ตอบกลับไม่ใช่ JSON:" >&2
    head -c 200 "$BODY" >&2
    exit 1
fi
```

## 20.6 Retry ด้วย exponential backoff + jitter

```bash
retry_curl() {
    local max=5 attempt=0 delay
    while (( attempt < max )); do
        if curl -fsS "$@"; then
            return 0
        fi
        local code=$?
        # 22 = HTTP >= 400 (จาก -f) → ไม่ retry ถ้าเป็น 4xx ที่ retry ไม่ช่วย
        (( attempt++ ))
        delay=$(( 2 ** attempt ))
        # jitter กัน thundering herd (บทที่ 12)
        delay=$(( delay + RANDOM % 3 ))
        echo "ล้มเหลว (exit $code) ลองใหม่ครั้งที่ $attempt ใน ${delay}s" >&2
        sleep "$delay"
    done
    return 1
}

retry_curl 'https://api.example.com/v1/books' -o out.json
```

curl มี retry ในตัวด้วย ใช้ได้เลยถ้าไม่ต้องการ logic พิเศษ:

```bash
curl --retry 5 --retry-delay 2 --retry-max-time 60 --retry-all-errors "$URL"
```

> ⚠️ **อย่า retry POST ที่ไม่ idempotent** — ใช้ `Idempotency-Key` (บทที่ 12)
> หรือจำกัด retry เฉพาะ GET

## 20.7 เคารพ rate limit

```bash
handle_429() {
    local wait
    wait=$(grep -i '^retry-after:' "$HEADERS" | tr -d '\r' | awk '{print $2}')
    wait="${wait:-60}"
    echo "โดน rate limit รอ ${wait}s" >&2
    sleep "$wait"
}

curl -sS -D "$HEADERS" -o "$BODY" -w '%{http_code}' "$URL"
```

`-D file` = เขียน response header ลงไฟล์ (แยกจาก body)

**ระหว่างการยิงหลายครั้ง ใส่หน่วงเวลาเสมอ:**

```bash
for id in "${IDS[@]}"; do
    curl -fsS "$B/api/books/$id" -o "out-$id.json"
    sleep 1        # ให้เกียรติ server ปลายทาง
done
```

## 20.8 โครงสร้างสคริปต์ที่ดี

```bash
#!/usr/bin/env bash
#
# submit.sh - ส่ง DOI เข้าระบบผ่าน API
#
# ใช้: ./submit.sh <doi>
# ต้องมี: API_TOKEN ใน environment

set -euo pipefail

readonly BASE_URL="${BASE_URL:-https://api.example.com}"
readonly SCRIPT_NAME="$(basename "$0")"

die()  { echo "$SCRIPT_NAME: $*" >&2; exit 1; }
log()  { echo "[$(date +%H:%M:%S)] $*" >&2; }

usage() {
    cat <<EOF
ใช้: $SCRIPT_NAME <doi>

ตัวแปรที่ต้องตั้ง:
  API_TOKEN   token สำหรับเรียก API
  BASE_URL    (ไม่บังคับ) ค่าเริ่มต้น: https://api.example.com
EOF
    exit 1
}

main() {
    [[ $# -eq 1 ]] || usage
    [[ -n "${API_TOKEN:-}" ]] || die "ต้องตั้ง API_TOKEN ก่อน"

    local doi="$1"
    local body
    body="$(mktemp)"
    trap 'rm -f "$body"' EXIT

    log "กำลังส่ง $doi"

    local code
    code=$(curl -sS -o "$body" -w '%{http_code}' \
                -H "Authorization: Bearer $API_TOKEN" \
                --data-urlencode "request=$doi" \
                "$BASE_URL/search")

    [[ "$code" == 2* ]] || die "ล้มเหลว HTTP $code: $(head -c 200 "$body")"

    jq -r '.id' "$body"
    log "สำเร็จ"
}

main "$@"
```

จุดที่ควรลอกไปใช้: `die`/`log` helper, `usage`, `readonly` สำหรับค่าคงที่,
`main "$@"` เพื่อให้อ่านจากบนลงล่างได้, และ trap ทำความสะอาด

## 20.9 เมื่อไรควรเลิกใช้ bash

**ย้ายไป Python เมื่อ:**

- ต้อง parse JSON ซับซ้อน (มากกว่าที่ jq หนึ่งบรรทัดทำได้)
- ต้องมี logic แบบ retry/state machine
- ต้องทำงานขนานหลาย request
- ต้องจัดการ error หลายกรณี
- สคริปต์ยาวเกิน ~150 บรรทัด

```python
import requests

session = requests.Session()                       # จัดการ cookie ให้เอง
session.headers["Authorization"] = f"Bearer {token}"

r = session.post(url, json={"query": q}, timeout=10)
r.raise_for_status()
print(r.json()["id"])
```

`requests.Session()` ทำหน้าที่เหมือน `-b`/`-c` ของ curl แต่อัตโนมัติ
— ถ้าโค้ดของคุณเริ่มมี `-b jar -c jar` เต็มไปหมด นั่นคือสัญญาณให้ย้าย

## แบบฝึกหัด

1. รัน `shellcheck lab/solutions/pow-flow.sh` — มันบ่นอะไรไหม แก้ให้หมด
2. ลบ `set -euo pipefail` ออกจากสคริปต์ แล้วทำให้ curl ล้มเหลว
   ดูว่าสคริปต์ทำงานต่อไปอย่างผิด ๆ ยังไง
3. เขียน `retry_curl` ในข้อ 20.6 แล้วทดสอบกับ URL ที่ไม่มีจริง
4. แก้ `pow-flow.sh` ให้จัดการกรณี 429 ตามข้อ 20.7
5. เขียนสคริปต์ตามโครงในข้อ 20.8 ที่ login เข้า lab แล้วดึงรายชื่อหนังสือออกมา
6. เขียนสคริปต์เดียวกันด้วย Python + `requests` แล้วเทียบว่าอันไหนอ่านง่ายกว่า

***
[⬅ Git](30-git.md) · [สารบัญ](../README.md) · [เขียนเทสต์ให้ API ➡](32-testing-with-pytest.md)
