#!/usr/bin/env python3
"""
แก้ PoW challenge แบบ ALTCHA v1 แล้วพิมพ์ payload (base64) ออก stdout

ใช้:
  curl -s http://127.0.0.1:8080/api/challenge | python3 lab/solve_pow.py

หลักการ: server ให้ challenge (sha256 hex) กับ salt มา
เราต้องหา number ที่ทำให้ sha256(salt + number) == challenge
วิธีเดียวคือไล่ลองตั้งแต่ 0 ไปเรื่อย ๆ = "งาน" ที่ต้องจ่ายด้วย CPU
"""

import base64
import hashlib
import json
import sys
import time


def solve(salt: str, target: str, max_number: int) -> int | None:
    """brute force หา number ที่ hash แล้วตรงกับ target"""
    target_bytes = bytes.fromhex(target)
    prefix = salt.encode()
    for n in range(max_number + 1):
        if hashlib.sha256(prefix + str(n).encode()).digest() == target_bytes:
            return n
    return None


def main() -> int:
    challenge = json.load(sys.stdin)

    if challenge.get("algorithm", "").upper() != "SHA-256":
        print(f"algorithm ไม่รองรับ: {challenge.get('algorithm')}", file=sys.stderr)
        return 1

    t0 = time.time()
    number = solve(challenge["salt"], challenge["challenge"], int(challenge["maxNumber"]))
    elapsed = time.time() - t0

    if number is None:
        print("หา solution ไม่เจอ (challenge อาจไม่ถูกต้อง)", file=sys.stderr)
        return 1

    print(f"เจอ number={number} ใน {elapsed:.2f} วินาที", file=sys.stderr)

    # payload ของ ALTCHA v1 = base64 ของ JSON ที่มี 5 field นี้
    payload = {
        "algorithm": challenge["algorithm"],
        "challenge": challenge["challenge"],
        "number": number,
        "salt": challenge["salt"],
        "signature": challenge["signature"],
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    print(base64.b64encode(raw).decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
