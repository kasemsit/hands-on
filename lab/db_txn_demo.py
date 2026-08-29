#!/usr/bin/env python3
"""lab บทที่ 71 — lost update และ transaction

    python3 lab/db_txn_demo.py

สาธิตด้วย sqlite ล้วน (มากับ Python) ว่า:
  1. อ่าน-แก้-เขียนโดยไม่มี transaction → เงินหาย (lost update)
  2. BEGIN IMMEDIATE → ตรงเป๊ะ
  3. rollback → error กลางคันแล้วไม่มีเงินหาย
"""
import os
import sqlite3
import threading
import time

DB = "/tmp/lab_bank.db"


def setup():
    if os.path.exists(DB):
        os.remove(DB)
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE account (id INT, balance INT)")
    c.execute("INSERT INTO account VALUES (1, 1000)")
    c.commit()
    c.close()


def final_balance():
    c = sqlite3.connect(DB)
    b = c.execute("SELECT balance FROM account WHERE id=1").fetchone()[0]
    c.close()
    return b


def run_threads(fn):
    setup()
    ts = [threading.Thread(target=fn) for _ in range(5)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return final_balance()


def unsafe():
    for _ in range(100):
        c = sqlite3.connect(DB, timeout=30)
        bal = c.execute("SELECT balance FROM account WHERE id=1").fetchone()[0]
        time.sleep(0.0001)                          # จำลองช่วงคิด
        c.execute("UPDATE account SET balance=? WHERE id=1", (bal - 1,))
        c.commit()
        c.close()


def safe():
    for _ in range(100):
        c = sqlite3.connect(DB, timeout=30)
        c.execute("BEGIN IMMEDIATE")                # ล็อกทันที
        bal = c.execute("SELECT balance FROM account WHERE id=1").fetchone()[0]
        c.execute("UPDATE account SET balance=? WHERE id=1", (bal - 1,))
        c.commit()
        c.close()


if __name__ == "__main__":
    u = run_threads(unsafe)
    print("=== ไม่มี transaction (5 thread ถอนคนละ 100) ===")
    print(f"  ควรเหลือ 500 · จริง {u}  "
          f"{'✅' if u == 500 else '🔴 เงินหาย ' + str(u - 500)}")

    s = run_threads(safe)
    print("\n=== BEGIN IMMEDIATE ===")
    print(f"  จริง {s}  {'✅ ตรง' if s == 500 else '🔴'}")
