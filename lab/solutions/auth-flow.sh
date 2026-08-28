#!/usr/bin/env bash
#
# เฉลยบทที่ 9-11: Basic auth / API key / Bearer token / refresh rotation
#
# รัน: bash lab/solutions/auth-flow.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8080}"

hr() { printf '%s\n' "────────────────────────────────────────────────"; }

# ── 1. Basic auth ────────────────────────────────────────────────
hr; echo "1. HTTP Basic auth"; hr

CODE="$(curl -sS -o /dev/null -w '%{http_code}' "$BASE_URL/basic")"
echo "ไม่ส่ง credential           → HTTP $CODE"

# -D - เขียน response header ออก stdout (แยกจาก body ที่โยนทิ้งด้วย -o)
echo "header ที่ server ขอมา     → $(curl -sS -D - -o /dev/null "$BASE_URL/basic" \
        | grep -i '^www-authenticate' | tr -d '\r')"

CODE="$(curl -sS -u myuser:mypass -o /dev/null -w '%{http_code}' "$BASE_URL/basic")"
echo "ส่ง -u myuser:mypass       → HTTP $CODE"

# ดูว่า curl แปลงเป็นอะไร แล้ว decode กลับ - base64 ไม่ใช่การเข้ารหัส
# บรรทัดที่ได้คือ "> Authorization: Basic bXl1c2Vy..." จึงเอาฟิลด์ที่ 4
AUTH="$(curl -sSv -u myuser:mypass -o /dev/null "$BASE_URL/basic" 2>&1 \
        | grep -i '^> authorization:' | tr -d '\r' | awk '{print $4}')"
echo "curl ส่ง                   → Authorization: Basic $AUTH"
echo "decode กลับได้             → $(echo "$AUTH" | base64 -d)"

# ── 2. API key ───────────────────────────────────────────────────
hr; echo "2. API key"; hr

curl -sS "$BASE_URL/api/keyed" | jq -r '"ไม่ส่ง key    → \(.error)"'
curl -sS -H 'X-API-Key: ผิด' "$BASE_URL/api/keyed" | jq -r '"key ผิด       → \(.error)"'
curl -sS -H 'X-API-Key: demo-key-123' "$BASE_URL/api/keyed" \
    | jq -r '"key ถูก       → owner=\(.owner) via=\(.via)"'

# query string ใช้ได้แต่ไม่ควร - มันติดใน access log และ Referer
curl -sS "$BASE_URL/api/keyed?api_key=demo-key-123" \
    | jq -r '"ผ่าน query    → via=\(.via)  ⚠️ หลีกเลี่ยง"'

# ── 3. Bearer token ──────────────────────────────────────────────
hr; echo "3. Bearer token"; hr

PAIR="$(curl -sS --json '{"username":"myuser","password":"mypass"}' "$BASE_URL/api/token")"
echo "$PAIR" | jq -r '"login สำเร็จ → token_type=\(.token_type) expires_in=\(.expires_in)s"'

ACCESS="$(jq -r .access_token <<< "$PAIR")"
REFRESH1="$(jq -r .refresh_token <<< "$PAIR")"

curl -sS "$BASE_URL/api/me" | jq -r '"ไม่ส่ง token  → \(.error)"'
curl -sS -H 'Authorization: Bearer มั่ว' "$BASE_URL/api/me" | jq -r '"token มั่ว     → \(.error)"'
curl -sS -H "Authorization: Bearer $ACCESS" "$BASE_URL/api/me" \
    | jq -r '"token ถูก     → user=\(.user) เหลืออีก \(.expires_in)s"'

# ── 4. Refresh rotation + reuse detection ────────────────────────
hr; echo "4. Refresh token rotation"; hr

refresh() {
    curl -sS --json "$(jq -nc --arg r "$1" '{refresh_token:$r}')" "$BASE_URL/api/refresh"
}

RESP="$(refresh "$REFRESH1")"
REFRESH2="$(jq -r '.refresh_token // empty' <<< "$RESP")"
echo "refresh ครั้งแรก → ได้ใบใหม่ ${REFRESH2:0:12}..."
echo "                  ใบเก่า ${REFRESH1:0:12}... ถูกเผาทิ้งแล้ว"

echo
echo "จำลองว่า token รั่ว: ผู้โจมตีเอาใบเก่ามาใช้ซ้ำ"
refresh "$REFRESH1" | jq -r '"  → \(.detail)"'

echo
echo "ผลกระทบ: ใบใหม่ที่ผู้ใช้จริงถืออยู่ก็ตายไปด้วย (ทั้ง family ถูกเพิกถอน)"
refresh "$REFRESH2" | jq -r '"  → \(.detail)"'

hr
cat <<'EOF'
สรุป
  Basic auth  ส่ง password ทุก request  → ไม่เหมาะกับ mobile
  API key     ไม่หมดอายุเอง             → เหมาะกับ server-to-server
  Bearer      อายุสั้น + refresh ได้     → เหมาะกับ mobile ที่สุด
  Rotation    ใบเก่าใช้ซ้ำ = ตรวจจับได้ว่า token รั่ว

⚠️ ข้อควรระวังในแอปจริง: ถ้ามีหลาย request เจอ 401 พร้อมกัน
   แล้วต่างคนต่างเรียก refresh จะทำลาย family ของตัวเอง
   → ต้องทำ single-flight ให้เรียก refresh ได้ทีละครั้ง (บทที่ 11)
EOF
