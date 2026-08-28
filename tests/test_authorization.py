"""
เทสต์ BOLA / IDOR — ตรงกับบทที่ 24

นี่คือเทสต์ที่ควรมีในทุกโปรเจกต์ที่มี API และเป็นเทสต์ที่
**ต้องใช้สองบัญชี** ถึงจะเขียนได้ — ด้วยบัญชีเดียวตรวจไม่เจอ

รัน:  .venv/bin/pytest tests/test_authorization.py -v
"""

import pytest
import requests

# order 1001, 1003 เป็นของ myuser · 1002, 1004 เป็นของ otheruser
MY_ORDERS = [1001, 1003]
OTHER_ORDERS = [1002, 1004]


@pytest.mark.parametrize("order_id", MY_ORDERS)
def test_เจ้าของดู_order_ตัวเองได้(base_url, auth, order_id):
    r = requests.get(f"{base_url}/api/v2/orders/{order_id}", headers=auth, timeout=5)
    assert r.status_code == 200
    assert r.json()["data"]["owner"] == "myuser"


@pytest.mark.parametrize("order_id", OTHER_ORDERS)
def test_ห้ามดู_order_ของคนอื่น(base_url, auth, order_id):
    """เทสต์หลักของบทที่ 24 — ถ้าอันนี้พัง ข้อมูลลูกค้ารั่ว"""
    r = requests.get(f"{base_url}/api/v2/orders/{order_id}", headers=auth, timeout=5)
    assert r.status_code != 200, f"BOLA: myuser เข้าถึง order {order_id} ของคนอื่นได้"


@pytest.mark.parametrize("order_id", OTHER_ORDERS)
def test_ตอบ_404_ไม่ใช่_403_เพื่อกันการไล่เดา(base_url, auth, order_id):
    """
    บทที่ 24.4 — 403 เท่ากับยอมรับว่า order นี้มีอยู่จริง
    ผู้โจมตีจะไล่นับได้ว่าระบบมีลูกค้ากี่ราย
    """
    r = requests.get(f"{base_url}/api/v2/orders/{order_id}", headers=auth, timeout=5)
    assert r.status_code == 404, "ควรตอบ 404 เพื่อไม่บอกใบ้ว่า id นี้มีอยู่"


def test_order_ที่ไม่มีจริงกับของคนอื่นต้องตอบเหมือนกัน(base_url, auth):
    """ถ้าตอบต่างกัน ผู้โจมตีก็ยังแยกออกอยู่ดีว่า id ไหนมีจริง"""
    ไม่มีจริง = requests.get(f"{base_url}/api/v2/orders/999999", headers=auth, timeout=5)
    ของคนอื่น = requests.get(f"{base_url}/api/v2/orders/1002", headers=auth, timeout=5)

    assert ไม่มีจริง.status_code == ของคนอื่น.status_code
    assert ไม่มีจริง.json().get("error") == ของคนอื่น.json().get("error")


def test_ไม่มี_token_ต้องเข้าไม่ได้(base_url):
    r = requests.get(f"{base_url}/api/v2/orders/1001", timeout=5)
    assert r.status_code == 401


def test_ทั้งสองฝ่ายเห็นเฉพาะของตัวเอง(base_url, token, other_token):
    """ตรวจแบบสมมาตร — กันกรณีที่เผลอ hard-code ชื่อ user ไว้"""
    for tok, mine, theirs in [
        (token, MY_ORDERS, OTHER_ORDERS),
        (other_token, OTHER_ORDERS, MY_ORDERS),
    ]:
        h = {"Authorization": f"Bearer {tok}"}
        for oid in mine:
            assert requests.get(f"{base_url}/api/v2/orders/{oid}",
                                headers=h, timeout=5).status_code == 200
        for oid in theirs:
            assert requests.get(f"{base_url}/api/v2/orders/{oid}",
                                headers=h, timeout=5).status_code == 404


# ── endpoint ที่มีช่องโหว่โดยเจตนา ────────────────────────
@pytest.mark.xfail(reason="v1 มีช่องโหว่ BOLA โดยเจตนา ไว้เทียบกับ v2 ในบทที่ 24",
                   strict=True)
@pytest.mark.parametrize("order_id", OTHER_ORDERS)
def test_v1_มีช่องโหว่_bola(base_url, auth, order_id):
    """
    xfail strict=True แปลว่า "เทสต์นี้ต้องพัง"
    ถ้าวันหนึ่งมีคนไปแก้ v1 ให้ปลอดภัย เทสต์นี้จะเตือนว่าเอกสารบทที่ 24
    ไม่ตรงกับโค้ดแล้ว
    """
    r = requests.get(f"{base_url}/api/v1/orders/{order_id}", headers=auth, timeout=5)
    assert r.status_code != 200
