#!/usr/bin/env python3
"""
เฉลยบทที่ 18: ให้ Playwright login แล้วส่ง cookie ต่อให้ curl

ใช้:
  python3 lab/solutions/playwright_cookies.py            # ใช้ Playwright จริง
  python3 lab/solutions/playwright_cookies.py --demo     # ทดสอบตัวแปลงโดยไม่ต้องมี Playwright

ต้องติดตั้งก่อน (เฉพาะโหมดปกติ):
  pip install playwright && playwright install chromium
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

BASE_URL = "http://127.0.0.1:8080"


# ---------------------------------------------------------------------------
# ส่วนที่สำคัญที่สุดของบทนี้: แปลง cookie ของ Playwright เป็น Netscape cookie jar
# ---------------------------------------------------------------------------
def cookies_to_netscape(cookies: list[dict]) -> str:
    """
    แปลง cookie จาก Playwright (storage_state) เป็นไฟล์ที่ curl -b อ่านได้

    รูปแบบ Netscape มี 7 คอลัมน์ คั่นด้วย TAB (ไม่ใช่ space!):
      domain  include_subdomains  path  secure  expires  name  value
    """
    lines = [
        "# Netscape HTTP Cookie File",
        "# สร้างโดย playwright_cookies.py",
        "",
    ]

    for c in cookies:
        domain = c["domain"]

        # Playwright ใช้ leading dot แทน "รวม subdomain ด้วย" เหมือน browser
        include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"

        # cookie ที่ไม่มีวันหมดอายุ (session cookie) จะได้ expires = -1
        expires = int(c.get("expires", -1))
        if expires < 0:
            expires = 0

        fields = [
            domain,
            include_subdomains,
            c.get("path", "/"),
            "TRUE" if c.get("secure") else "FALSE",
            str(expires),
            c["name"],
            c["value"],
        ]

        # curl ทำเครื่องหมาย HttpOnly ด้วย prefix พิเศษหน้าชื่อ domain
        prefix = "#HttpOnly_" if c.get("httpOnly") else ""
        lines.append(prefix + "\t".join(fields))

    return "\n".join(lines) + "\n"


def cookies_to_header(cookies: list[dict]) -> str:
    """อีกทางเลือก: ทำเป็น string สำหรับ curl -b 'a=1; b=2'"""
    return "; ".join(f"{c['name']}={c['value']}" for c in cookies)


# ---------------------------------------------------------------------------
def login_with_playwright(storage_path: Path) -> list[dict]:
    """เปิด browser จริง login แล้วคืน cookie ที่ได้"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ยังไม่ได้ติดตั้ง Playwright:\n"
              "  pip install playwright && playwright install chromium\n"
              "หรือลองโหมดทดสอบตัวแปลง: --demo", file=sys.stderr)
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("[1/3] เปิดหน้า login ด้วย browser จริง...")
        page.goto(f"{BASE_URL}/login")

        # ไม่ต้องยุ่งกับ CSRF token เลย - browser จัดการให้เอง
        page.fill("input[name='username']", "myuser")
        page.fill("input[name='password']", "mypass")
        page.click("button[type='submit']")
        page.wait_for_url("**/dashboard")

        print(f"      login สำเร็จ: {page.url}")

        # เก็บ cookie + localStorage ทั้งหมด
        context.storage_state(path=str(storage_path))
        cookies = context.cookies()

        browser.close()

    return cookies


DEMO_COOKIES = [
    {"name": "sid", "value": "demo123abc", "domain": "127.0.0.1", "path": "/",
     "expires": -1, "httpOnly": True, "secure": False, "sameSite": "Lax"},
    {"name": "theme", "value": "dark", "domain": ".example.com", "path": "/",
     "expires": 2000000000, "httpOnly": False, "secure": True, "sameSite": "Lax"},
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true",
                    help="ใช้ cookie ตัวอย่าง ไม่ต้องมี Playwright")
    ap.add_argument("--jar", default="", help="ที่เก็บ cookie jar (ค่าเริ่มต้น: ไฟล์ชั่วคราว)")
    args = ap.parse_args()

    jar_path = Path(args.jar) if args.jar else Path(tempfile.mkstemp(suffix=".txt")[1])
    storage_path = jar_path.with_suffix(".storage.json")

    if args.demo:
        print("[demo] ใช้ cookie ตัวอย่าง (ไม่เปิด browser)")
        cookies = DEMO_COOKIES
        storage_path.write_text(json.dumps({"cookies": cookies, "origins": []}, indent=2))
    else:
        cookies = login_with_playwright(storage_path)

    print(f"[2/3] ได้ cookie {len(cookies)} ตัว → แปลงเป็น Netscape format")
    jar_path.write_text(cookies_to_netscape(cookies))
    print(f"      cookie jar: {jar_path}")
    print("---")
    print(jar_path.read_text(), end="")
    print("---")

    if args.demo:
        print("[3/3] ข้ามการยิง curl (โหมด demo)")
        return 0

    print("[3/3] ส่งต่อให้ curl - ไม่ต้อง login ซ้ำ")
    result = subprocess.run(
        ["curl", "-fsS", "-b", str(jar_path), f"{BASE_URL}/dashboard"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"curl ล้มเหลว: {result.stderr}", file=sys.stderr)
        return 1

    for line in result.stdout.splitlines():
        if "สวัสดี" in line or "session id" in line:
            print("      " + line.strip())

    print("\nสำเร็จ - Playwright login ครั้งเดียว แล้ว curl ใช้ session ต่อได้เลย")
    return 0


if __name__ == "__main__":
    sys.exit(main())
