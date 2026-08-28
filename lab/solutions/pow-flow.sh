#!/usr/bin/env bash
# เฉลยบทที่ 9: ผ่านด่าน PoW CAPTCHA ทั้ง flow ด้วย curl + python
#
#   GET /api/challenge  ->  solve  ->  POST /api/solution  ->  GET /api/protected
#
# รัน: bash lab/solutions/pow-flow.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8080}"

COOKIE_JAR="$(mktemp)"
CHALLENGE_FILE="$(mktemp)"
trap 'rm -f "$COOKIE_JAR" "$CHALLENGE_FILE"' EXIT

echo "[1/4] ขอ challenge..."
curl -fsS -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
    "$BASE_URL/api/challenge" -o "$CHALLENGE_FILE"
jq '{algorithm, maxNumber, salt}' "$CHALLENGE_FILE"

echo "[2/4] แก้ PoW (ตรงนี้แหละที่กิน CPU)..."
PAYLOAD="$(python3 "$(dirname "$0")/../solve_pow.py" < "$CHALLENGE_FILE")"
echo "payload (60 ตัวแรก): ${PAYLOAD:0:60}..."

echo "[3/4] ส่งคำตอบ..."
# --argjson ไม่ได้ เพราะ payload เป็น string -> ใช้ --arg แล้วให้ jq ทำ JSON escaping ให้
BODY="$(jq -nc --arg p "$PAYLOAD" '{captcha: $p}')"

curl -fsS -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
    -H 'Content-Type: application/json' \
    --data "$BODY" \
    "$BASE_URL/api/solution" | jq .

echo "[4/4] เข้า endpoint ที่ถูกป้องกัน..."
curl -fsS -b "$COOKIE_JAR" "$BASE_URL/api/protected" | jq '{ok, note, count: (.data | length)}'

echo
echo "สำเร็จ — cookie ที่ได้จากขั้นที่ 3 คือสิ่งที่ทำให้ขั้นที่ 4 ผ่าน"
