# บทที่ 32 · เขียนเทสต์ให้ API

> ตลอดคอร์สนี้ผมพูดคำว่า "เขียนเทสต์ใส่ CI" หลายครั้ง — โดยไม่เคยสอนวิธีเขียน
> บทนี้ปิดช่องว่างนั้น และเราจะเขียนเทสต์ **BOLA จาก[บทที่ 24](24-authorization-and-bola.md)** ที่ใช้ได้จริง

โค้ดทั้งหมดในบทนี้อยู่ในโฟลเดอร์ [tests/](../tests/) รันได้เลย

## 32.1 ทำไมต้องมีเทสต์อัตโนมัติ

คุณทดสอบด้วยมือมาตลอดทั้งคอร์ส — ยิง `curl` ดูผล ซึ่งใช้ได้ดีตอนเรียน
แต่มีปัญหาเมื่อระบบโต:

| ทดสอบด้วยมือ | เทสต์อัตโนมัติ |
|--------------|----------------|
| ทดสอบเฉพาะที่นึกออก | ทดสอบทุกอย่างทุกครั้ง |
| ลืมทดสอบของเก่าหลังแก้โค้ด | จับ regression ให้ทันที |
| อธิบายให้คนอื่นฟังยาก | เทสต์คือเอกสารที่รันได้ |
| ตรวจ BOLA 20 endpoint = 40 คำสั่ง | รันทีเดียว |

**เหตุผลที่หนักที่สุดสำหรับงานความปลอดภัย:** ช่องโหว่อย่าง BOLA ([บทที่ 24](24-authorization-and-bola.md))
**กลับมาใหม่ได้เสมอ** เมื่อมีคนเพิ่ม endpoint ใหม่แล้วลืมเช็ค owner
เทสต์คือสิ่งเดียวที่กันไม่ให้มันกลับมา

## 32.2 เตรียมเครื่อง

```bash
python3 -m venv .venv
.venv/bin/pip install pytest requests
```

> ⚠️ **บน Ubuntu/Debian สมัยใหม่ `pip install` ตรง ๆ จะถูกปฏิเสธ**
> ```
> error: externally-managed-environment
> ```
> เป็นกฎ PEP 668 ที่กัน pip ไปทับ package ของระบบ **ให้ใช้ venv เสมอ**
> อย่าใช้ `--break-system-packages` เพราะชื่อมันบอกอยู่แล้วว่าทำอะไร

## 32.3 เทสต์แรก

pytest หาไฟล์ที่ชื่อ `test_*.py` และฟังก์ชันที่ชื่อ `test_*` ให้เอง

```python
# tests/test_smoke.py
import requests

def test_หน้าแรกตอบ_200():
    r = requests.get("http://127.0.0.1:8080/", timeout=5)
    assert r.status_code == 200
```

```bash
.venv/bin/pytest -v
```

**ไม่ต้องมี class ไม่ต้อง import framework** — แค่ฟังก์ชันกับ `assert`
นี่คือเหตุผลที่ pytest ชนะ `unittest` ในทางปฏิบัติ

เวลาพัง pytest จะแสดงค่าจริงให้ดูเอง:

```
E       assert 404 == 200
E        +  where 404 = <Response [404]>.status_code
```

## 32.4 Fixture — ของกลางที่เตรียมให้อัตโนมัติ

ปัญหาของเทสต์ข้างบน: **มันต้องให้คุณเปิด lab server เองก่อน** ถ้าลืมก็พังทั้งชุด

**fixture** คือฟังก์ชันที่เตรียมของให้เทสต์ แล้วเก็บกวาดให้เมื่อจบ

```python
# tests/conftest.py — pytest โหลดไฟล์นี้ให้เอง ไม่ต้อง import
@pytest.fixture(scope="session")
def base_url():
    proc = subprocess.Popen([sys.executable, str(tmp)])   # setup

    deadline = time.time() + 10
    while time.time() < deadline:
        if _port_open(PORT):
            break
        time.sleep(0.05)
    else:
        proc.kill()
        pytest.fail("lab server ไม่ขึ้นภายใน 10 วินาที")

    yield BASE          # ← เทสต์ทำงานตรงนี้

    proc.terminate()    # teardown — ทำแม้เทสต์จะพัง
    proc.wait(timeout=5)
```

จากนั้นเทสต์ไหนอยากได้ ก็แค่รับเป็นพารามิเตอร์:

```python
def test_อะไรสักอย่าง(base_url):        # pytest ส่ง fixture ให้เอง
    r = requests.get(f"{base_url}/api/books")
```

| `scope` | สร้างใหม่เมื่อไร | ใช้กับ |
|---------|-----------------|--------|
| `function` (ค่าเริ่มต้น) | ทุกเทสต์ | ของที่ต้องสะอาดทุกครั้ง |
| `module` | ทุกไฟล์ | |
| `session` | ครั้งเดียวทั้งชุด | **server, ฐานข้อมูล** — แพงเกินกว่าจะสร้างซ้ำ |

> **สองจุดสำคัญในโค้ดข้างบน**
>
> 1. **รอจนพอร์ตเปิดจริง อย่าใช้ `sleep(2)` ตายตัว** — เครื่องเร็วก็เสียเวลาเปล่า
>    เครื่องช้าก็ยังไม่ทัน กลายเป็นเทสต์ที่พังแบบสุ่ม (flaky test)
> 2. **`yield` ไม่ใช่ `return`** — โค้ดหลัง `yield` คือ teardown ที่ทำงานเสมอ
>    แม้เทสต์จะพังกลางคัน

## 32.5 เทสต์เดียว หลายเคส — `parametrize`

```python
@pytest.mark.parametrize("key,expected", [
    ("demo-key-123", 200),
    ("wrong-key",    403),
    (None,           401),
])
def test_api_key(base_url, key, expected):
    headers = {"X-API-Key": key} if key else {}
    r = requests.get(f"{base_url}/api/keyed", headers=headers, timeout=5)
    assert r.status_code == expected
```

pytest นับเป็น **3 เทสต์แยกกัน** — พังอันไหนก็รู้ทันทีว่าเคสไหน

```
tests/test_auth.py::test_api_key[demo-key-123-200] PASSED
tests/test_auth.py::test_api_key[wrong-key-403] PASSED
tests/test_auth.py::test_api_key[None-401] PASSED
```

> ⚠️ **ค่าใน header ต้องเป็น ASCII เท่านั้น** — ตอนเขียนเทสต์ชุดนี้ผมใส่
> `{"X-API-Key": "ผิด"}` แล้วได้ `UnicodeEncodeError: 'latin-1' codec can't encode`
> **ตั้งแต่ยังไม่ได้ยิงออกไปด้วยซ้ำ** ซึ่งตรงกับกฎใน[บทที่ 1.9](01-http-basics.md) พอดี
> — เทสต์จับกฎของ HTTP ให้เราโดยไม่ตั้งใจ

## 32.6 เทสต์ BOLA — ของจริงที่ควรมีทุกโปรเจกต์

นี่คือเทสต์ที่สำคัญที่สุดในบทนี้ และ **ต้องใช้สองบัญชีถึงจะเขียนได้**

```python
# order 1001, 1003 เป็นของ myuser · 1002, 1004 เป็นของ otheruser
MY_ORDERS    = [1001, 1003]
OTHER_ORDERS = [1002, 1004]

@pytest.mark.parametrize("order_id", OTHER_ORDERS)
def test_ห้ามดู_order_ของคนอื่น(base_url, auth, order_id):
    r = requests.get(f"{base_url}/api/v2/orders/{order_id}", headers=auth, timeout=5)
    assert r.status_code != 200, f"BOLA: เข้าถึง order {order_id} ของคนอื่นได้"


@pytest.mark.parametrize("order_id", OTHER_ORDERS)
def test_ตอบ_404_ไม่ใช่_403(base_url, auth, order_id):
    """403 = ยอมรับว่า order นี้มีจริง → ผู้โจมตีไล่นับลูกค้าได้ (บทที่ 24.4)"""
    r = requests.get(f"{base_url}/api/v2/orders/{order_id}", headers=auth, timeout=5)
    assert r.status_code == 404
```

**เทสต์แบบสมมาตร** กันกรณีที่เผลอ hard-code ชื่อ user ไว้ในโค้ด:

```python
def test_ทั้งสองฝ่ายเห็นเฉพาะของตัวเอง(base_url, token, other_token):
    for tok, mine, theirs in [
        (token,       MY_ORDERS,    OTHER_ORDERS),
        (other_token, OTHER_ORDERS, MY_ORDERS),
    ]:
        h = {"Authorization": f"Bearer {tok}"}
        for oid in mine:
            assert requests.get(f"{base_url}/api/v2/orders/{oid}", headers=h).status_code == 200
        for oid in theirs:
            assert requests.get(f"{base_url}/api/v2/orders/{oid}", headers=h).status_code == 404
```

## 32.7 `xfail` — เทสต์ที่ "ต้องพัง"

lab มี `/api/v1/orders` ที่มีช่องโหว่ BOLA **โดยเจตนา** ไว้เทียบกับ v2

```python
@pytest.mark.xfail(reason="v1 มีช่องโหว่โดยเจตนา ไว้เทียบในบทที่ 24", strict=True)
@pytest.mark.parametrize("order_id", OTHER_ORDERS)
def test_v1_มีช่องโหว่_bola(base_url, auth, order_id):
    r = requests.get(f"{base_url}/api/v1/orders/{order_id}", headers=auth, timeout=5)
    assert r.status_code != 200
```

**`strict=True` สำคัญมาก** — ถ้าวันหนึ่งมีคนไปแก้ v1 ให้ปลอดภัย เทสต์นี้จะ
**รายงานว่าล้มเหลว** (เพราะมันผ่านทั้งที่ควรพัง) เตือนว่าเอกสาร[บทที่ 24](24-authorization-and-bola.md)
ไม่ตรงกับโค้ดแล้ว

## 32.8 จัดระเบียบและรัน

`pytest.ini` ที่ราก:

```ini
[pytest]
testpaths = tests
markers =
    slow: เทสต์ที่ใช้เวลานาน (ข้ามด้วย -m "not slow")
addopts = -q --strict-markers
```

`--strict-markers` = ถ้าพิมพ์ชื่อ marker ผิดจะ error ทันที ไม่ปล่อยผ่านเงียบ ๆ

```bash
.venv/bin/pytest                      # ทั้งหมด
.venv/bin/pytest -v                   # เห็นชื่อทุกเทสต์
.venv/bin/pytest -m "not slow"        # ข้ามตัวช้า
.venv/bin/pytest tests/test_auth.py   # เฉพาะไฟล์
.venv/bin/pytest -k "bola"            # เฉพาะที่ชื่อมีคำว่า bola
.venv/bin/pytest -x                   # หยุดทันทีที่พังตัวแรก
.venv/bin/pytest --lf                 # รันเฉพาะที่พังรอบที่แล้ว
```

`--lf` (last failed) ช่วยมากตอนไล่แก้ — ไม่ต้องรอทั้งชุด

**ผลจริงจากชุดเทสต์ของคอร์สนี้:**

```
......................xx                                     [100%]
22 passed, 1 deselected, 2 xfailed in 0.16s
```

## 32.9 เทสต์อะไรบ้างสำหรับ API

เรียงตามความคุ้มค่า:

| ลำดับ | เทสต์อะไร | ทำไมคุ้ม |
|-------|-----------|----------|
| 1 | **BOLA / authorization** | ช่องโหว่อันดับ 1 และ scanner จับไม่ได้ |
| 2 | **auth flow** — 401 vs 403, refresh rotation | พังแล้วผู้ใช้เข้าไม่ได้ทั้งระบบ |
| 3 | **contract** — response มี field ครบไหม ชนิดถูกไหม | กัน breaking change กับแอปเก่า |
| 4 | **validation** — ส่งขยะเข้าไปแล้วตอบ 4xx ไม่ใช่ 500 | |
| 5 | **จำนวน query** ([บทที่ 27.1](27-database-and-performance.md)) | กัน N+1 กลับมา |
| 6 | edge case ทางธุรกิจ | |

**สิ่งที่ไม่ต้องเทสต์:** getter/setter, โค้ด framework, สิ่งที่ type checker จับได้อยู่แล้ว

> **อย่าไล่ล่า coverage 100%** — coverage 60% ที่ครอบคลุมเรื่องข้างบนนี้
> มีค่ากว่า 95% ที่เต็มไปด้วยเทสต์ getter

## 32.10 เทสต์ที่พังแบบสุ่ม (flaky) คือศัตรู

เทสต์ที่บางทีผ่านบางทีพัง **แย่กว่าไม่มีเทสต์** เพราะคนจะเริ่มเมินเวลามันแดง

สาเหตุที่พบบ่อยและวิธีแก้:

| สาเหตุ | แก้ |
|--------|-----|
| `sleep()` ตายตัว | รอจนเงื่อนไขเป็นจริง (ดูข้อ 32.4) |
| เทสต์แชร์ state กัน | ให้แต่ละเทสต์สร้างข้อมูลของตัวเอง |
| ลำดับการรันมีผล | ต้องรันสลับลำดับแล้วยังผ่าน (`pytest -p no:randomly` เพื่อตรวจ) |
| พึ่งพาเวลาจริง / timezone | ตรึงเวลาด้วย `freezegun` |
| ยิง API ภายนอกจริง | ใช้ mock หรือ server ปลอม (`nc` — ภาคผนวก A) |

## 32.11 ใส่ใน CI

```yaml
# .github/workflows/test.yml
name: tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install pytest requests
      - run: pytest -m "not slow"
```

**เทสต์ที่ไม่ได้รันอัตโนมัติ = เทสต์ที่ไม่มี** เพราะสุดท้ายจะไม่มีใครรันเอง

ต่อยอด: `git bisect run pytest` ([บทที่ 30.10](30-git.md)) จะหาให้ว่า commit ไหนทำพัง

## แบบฝึกหัด

1. รันชุดเทสต์ที่มีอยู่ให้ผ่าน:
   ```bash
   python3 -m venv .venv && .venv/bin/pip install pytest requests
   .venv/bin/pytest -m "not slow" -v
   ```
2. **ทำให้เทสต์จับ BOLA ได้จริง** — แก้ `api_order` ใน [lab/server.py](../lab/server.py)
   ให้ v2 ลืมเช็ค owner (เอาเงื่อนไข `order["owner"] != user` ออก) แล้วรันเทสต์
   ต้องเห็นสีแดง จากนั้นแก้กลับ
3. เขียนเทสต์ contract: ยืนยันว่า `/api/books` ตอบ `items` เป็น list และทุกตัวมี
   `id`, `title`, `author`, `tag`
4. เขียนเทสต์ที่ยืนยันว่า `/api/cached` ตอบ **304** เมื่อส่ง `If-None-Match` กลับไป
5. เขียนเทสต์ว่า `/api/solution` ปฏิเสธ payload ที่ไม่ใช่ base64 ([บทที่ 16](16-altcha-pow.md))
6. ลองใส่ marker ผิดชื่อ เช่น `@pytest.mark.slowww` — `--strict-markers` จับได้ไหม
7. เขียน `.github/workflows/test.yml` แล้ว push ขึ้น GitHub ดูว่ารันจริงไหม

***
[⬅ เขียน bash ให้ปลอดภัยและไม่พังเงียบ ](20-shell-scripting-for-curl.md) · [สารบัญ](../README.md) · [Concurrency และ async ➡](33-concurrency-and-async.md)
