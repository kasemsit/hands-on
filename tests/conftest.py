"""
ของกลางที่เทสต์ทุกไฟล์ใช้ร่วมกัน (pytest เรียกไฟล์นี้ว่า conftest)

pytest จะโหลดไฟล์นี้ให้อัตโนมัติ ไม่ต้อง import
fixture ที่ประกาศไว้ที่นี่ เทสต์ทุกไฟล์ในโฟลเดอร์เรียกใช้ได้เลย
"""

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "lab" / "server.py"
HOST, PORT = "127.0.0.1", 8099          # ใช้คนละ port กับตัวที่เปิดไว้อ่านเอง
BASE = f"http://{HOST}:{PORT}"


def _port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.2)
        return s.connect_ex((HOST, port)) == 0


@pytest.fixture(scope="session")
def base_url():
    """
    เปิด lab server หนึ่งตัวสำหรับเทสต์ทั้ง session แล้วปิดให้เมื่อจบ

    scope="session" = เปิดครั้งเดียวใช้ทุกเทสต์ (เร็วกว่าเปิด-ปิดทุกครั้ง)
    ทุกอย่างก่อน yield คือ setup ทุกอย่างหลัง yield คือ teardown
    """
    src = SERVER.read_text().replace("PORT = 8080", f"PORT = {PORT}")
    tmp = ROOT / "lab" / "_server_test.py"
    tmp.write_text(src)

    proc = subprocess.Popen(
        [sys.executable, str(tmp)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    # รอจน server พร้อมจริง — อย่าใช้ sleep ตายตัว เพราะเครื่องช้า/เร็วไม่เท่ากัน
    deadline = time.time() + 10
    while time.time() < deadline:
        if _port_open(PORT):
            break
        time.sleep(0.05)
    else:
        proc.kill()
        tmp.unlink(missing_ok=True)
        pytest.fail(f"lab server ไม่ขึ้นภายใน 10 วินาที (port {PORT})")

    yield BASE

    proc.terminate()
    proc.wait(timeout=5)
    tmp.unlink(missing_ok=True)


@pytest.fixture
def session(base_url):
    """requests.Session เก็บ cookie ให้อัตโนมัติ — เหมือน curl -b/-c (บทที่ 4)"""
    with requests.Session() as s:
        s.headers["User-Agent"] = "lab-tests/1.0"
        yield s


@pytest.fixture
def token(base_url):
    """access token ของ myuser — ใช้ในเทสต์ที่ต้อง auth"""
    r = requests.post(f"{base_url}/api/token",
                      json={"username": "myuser", "password": "mypass"}, timeout=5)
    r.raise_for_status()
    return r.json()["access_token"]


@pytest.fixture
def other_token(base_url):
    """access token ของ otheruser — จำเป็นสำหรับเทสต์ BOLA (บทที่ 24)"""
    r = requests.post(f"{base_url}/api/token",
                      json={"username": "otheruser", "password": "otherpass"}, timeout=5)
    r.raise_for_status()
    return r.json()["access_token"]


@pytest.fixture
def auth(token):
    """header สำเร็จรูปสำหรับ myuser"""
    return {"Authorization": f"Bearer {token}"}
