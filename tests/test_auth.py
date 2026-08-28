"""
เทสต์เรื่อง authentication — ตรงกับบทที่ 9 และ 11

รัน:  .venv/bin/pytest tests/test_auth.py -v
"""

import time

import pytest
import requests


# ── Basic auth (บทที่ 9.2) ────────────────────────────────
def test_basic_auth_ไม่ส่ง_credential_ต้องได้_401(base_url):
    r = requests.get(f"{base_url}/basic", timeout=5)
    assert r.status_code == 401
    # ต้องบอกด้วยว่าให้ auth แบบไหน ไม่งั้น client ไม่รู้จะทำยังไงต่อ
    assert "Basic" in r.headers.get("WWW-Authenticate", "")


def test_basic_auth_ส่งถูกต้องต้องผ่าน(base_url):
    r = requests.get(f"{base_url}/basic", auth=("myuser", "mypass"), timeout=5)
    assert r.status_code == 200


# ── API key (บทที่ 9.3) ───────────────────────────────────
@pytest.mark.parametrize("key,expected", [
    ("demo-key-123", 200),
    ("wrong-key", 403),
    (None, 401),
])
def test_api_key(base_url, key, expected):
    """parametrize = เทสต์เดียวรันหลายเคส เห็นผลแยกกันเวลาพัง"""
    headers = {"X-API-Key": key} if key else {}
    r = requests.get(f"{base_url}/api/keyed", headers=headers, timeout=5)
    assert r.status_code == expected


# ── Bearer token (บทที่ 9.4) ──────────────────────────────
def test_token_มีครบทุก_field_ตามมาตรฐาน_oauth(base_url):
    r = requests.post(f"{base_url}/api/token",
                      json={"username": "myuser", "password": "mypass"}, timeout=5)
    assert r.status_code == 200
    body = r.json()
    for field in ("access_token", "refresh_token", "token_type", "expires_in"):
        assert field in body, f"ขาด field {field}"
    assert body["token_type"] == "Bearer"
    assert isinstance(body["expires_in"], int)


def test_login_ผิดต้องได้_401_และไม่บอกใบ้(base_url):
    """
    บทที่ 11.10 — ต้องตอบเหมือนกันทั้งกรณี user ไม่มี และ password ผิด
    ไม่งั้นผู้โจมตีไล่หาได้ว่าบัญชีไหนมีอยู่จริง (user enumeration)
    """
    r1 = requests.post(f"{base_url}/api/token",
                       json={"username": "myuser", "password": "ผิด"}, timeout=5)
    r2 = requests.post(f"{base_url}/api/token",
                       json={"username": "ไม่มีคนนี้", "password": "อะไรก็ได้"}, timeout=5)

    assert r1.status_code == r2.status_code == 401
    assert r1.json()["error"] == r2.json()["error"], "ข้อความต่างกัน = บอกใบ้ว่าบัญชีไหนมีจริง"


# ⚠️ ค่าใน header ต้องเป็น ASCII เท่านั้น (บทที่ 1.9 และ 6.7)
# ถ้าใส่ภาษาไทยลงไป requests จะโยน UnicodeEncodeError ตั้งแต่ยังไม่ได้ยิงออกไป
@pytest.mark.parametrize("header,expected", [
    (None,                                      401),
    ({"Authorization": "Bearer invalid-token"}, 401),
    ({"Authorization": "Token abc123"},         401),   # ไม่มีคำว่า Bearer
])
def test_me_ปฏิเสธ_token_ที่ใช้ไม่ได้(base_url, header, expected):
    r = requests.get(f"{base_url}/api/me", headers=header or {}, timeout=5)
    assert r.status_code == expected


def test_me_ใช้ได้เมื่อ_token_ถูก(base_url, auth):
    r = requests.get(f"{base_url}/api/me", headers=auth, timeout=5)
    assert r.status_code == 200
    assert r.json()["user"] == "myuser"


# ── Refresh token rotation (บทที่ 11.4) ───────────────────
def test_refresh_ได้คู่ใหม่และใบเก่าใช้ไม่ได้(base_url):
    pair = requests.post(f"{base_url}/api/token",
                         json={"username": "myuser", "password": "mypass"},
                         timeout=5).json()
    old = pair["refresh_token"]

    new_pair = requests.post(f"{base_url}/api/refresh",
                             json={"refresh_token": old}, timeout=5).json()
    assert "refresh_token" in new_pair
    assert new_pair["refresh_token"] != old, "ต้องหมุนใบใหม่ ไม่ใช่คืนใบเดิม"


def test_ใช้_refresh_ซ้ำต้องเพิกถอนทั้ง_family(base_url):
    """
    นี่คือกลไกที่สำคัญที่สุดของบทที่ 11 — ถ้าเทสต์นี้พัง
    แปลว่า token ที่รั่วไปแล้วยังใช้ได้เรื่อย ๆ
    """
    pair = requests.post(f"{base_url}/api/token",
                         json={"username": "myuser", "password": "mypass"},
                         timeout=5).json()
    r1 = pair["refresh_token"]

    r2 = requests.post(f"{base_url}/api/refresh",
                       json={"refresh_token": r1}, timeout=5).json()["refresh_token"]

    # ผู้โจมตีเอาใบเก่ามาใช้
    reuse = requests.post(f"{base_url}/api/refresh",
                          json={"refresh_token": r1}, timeout=5)
    assert reuse.status_code == 401

    # ใบที่ผู้ใช้จริงถืออยู่ต้องตายไปด้วย
    after = requests.post(f"{base_url}/api/refresh",
                          json={"refresh_token": r2}, timeout=5)
    assert after.status_code == 401, "เพิกถอนไม่ครบ family — token ที่รั่วยังใช้ได้"


@pytest.mark.slow
def test_access_token_หมดอายุจริง(base_url, token):
    """
    lab ตั้ง access token ไว้ 120 วินาที เทสต์นี้จึงช้า
    ทำเครื่องหมาย slow ไว้เพื่อข้ามได้: pytest -m "not slow"
    """
    time.sleep(121)
    r = requests.get(f"{base_url}/api/me",
                     headers={"Authorization": f"Bearer {token}"}, timeout=5)
    assert r.status_code == 401
