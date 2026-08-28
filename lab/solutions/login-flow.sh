#!/usr/bin/env bash
#
# เฉลยบทที่ 3-5: login ผ่าน CSRF + cookie + redirect ด้วย curl ล้วน
#
# รัน: bash lab/solutions/login-flow.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8080}"

JAR="$(mktemp)"
FORM="$(mktemp)"
trap 'rm -f "$JAR" "$FORM"' EXIT

echo "[1/4] โหลดหน้า login — เก็บ cookie และ CSRF token"
curl -fsS -c "$JAR" "$BASE_URL/login" -o "$FORM"

# -c เขียน cookie ที่ server ตั้งลงไฟล์ ดูได้เลย
echo "      cookie ที่ได้:"
# บรรทัด cookie มี 7 คอลัมน์คั่นด้วย tab เสมอ
# (บรรทัดที่ขึ้นต้นด้วย #HttpOnly_ ก็เป็น cookie ไม่ใช่ comment)
awk -F'\t' 'NF==7 {print "        " $0}' "$JAR"

# hidden field ต้องดึงออกมาส่งกลับไปด้วย ไม่งั้นโดน 403
TOKEN="$(grep -oP 'name="csrf_token" value="\K[^"]+' "$FORM")"
echo "      csrf_token: $TOKEN"

echo
echo "[2/4] ลอง POST โดยไม่ส่ง cookie — ควรถูกปฏิเสธ"
CODE="$(curl -sS -o /dev/null -w '%{http_code}' \
        -X POST "$BASE_URL/login" \
        -d "csrf_token=$TOKEN" -d 'username=myuser' -d 'password=mypass')"
echo "      ได้ HTTP $CODE (server ไม่รู้จัก session)"

echo
echo "[3/4] POST จริง — พร้อม cookie + token + ตาม redirect"
# -b อ่าน cookie เดิม, -c เขียน cookie ใหม่ที่ได้หลัง login กลับลงไฟล์
#
# ⚠️ ห้ามใส่ -X POST ตรงนี้! -d ทำให้เป็น POST อยู่แล้ว
#    ถ้าใส่ -X POST คู่กับ -L curl จะ POST ซ้ำไปที่ /dashboard แล้วได้ 404
#    (กับดักข้อ 5.3 - ลองเติม -X POST ดูเองได้ เพื่อให้เห็นกับตา)
curl -fsS -b "$JAR" -c "$JAR" -L \
    "$BASE_URL/login" \
    -d "csrf_token=$TOKEN" \
    -d 'username=myuser' \
    --data-urlencode 'password=mypass' \
    -o /dev/null \
    -w '      จบที่ %{url_effective} (ผ่าน redirect %{num_redirects} ครั้ง)\n'

echo
echo "[4/4] เข้าหน้าที่ต้อง login"
curl -fsS -b "$JAR" "$BASE_URL/dashboard" \
    | grep -oE '(สวัสดี|session id).*' \
    | sed 's/<[^>]*>//g; s/^/      /'

echo
echo "สำเร็จ — cookie ใน $JAR คือสิ่งที่ทำให้ขั้นที่ 4 ผ่านโดยไม่ต้อง login ซ้ำ"
