#!/usr/bin/env python3
"""
Lab สำหรับบทที่ 27: ทำไม API ถึงช้าเมื่อข้อมูลโตขึ้น

รัน: python3 lab/db_demo.py

ใช้ sqlite3 ที่มากับ Python (ไม่ต้องลงอะไร) สร้างข้อมูลจำลองในหน่วยความจำ
แล้ววัดเวลาจริงของ 3 ปัญหาคลาสสิก:

  1. N+1 query        - ยิง query ในลูป
  2. ไม่มี index       - full table scan
  3. SELECT *         - ดึงข้อมูลที่ไม่ได้ใช้

ตัวเลขที่ได้จะต่างกันตามเครื่อง แต่ "อัตราส่วน" จะใกล้เคียงกันเสมอ
"""

import sqlite3
import time

N_USERS = 2_000
N_ORDERS = 50_000


def timed(label: str):
    """context manager วัดเวลา"""
    class T:
        def __enter__(self):
            self.t0 = time.perf_counter()
            return self

        def __exit__(self, *a):
            self.ms = (time.perf_counter() - self.t0) * 1000
            print(f"  {label:<44} {self.ms:8.1f} ms")
    return T()


def build_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE users  (id INTEGER PRIMARY KEY, name TEXT, bio TEXT);
        CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER,
                             item TEXT, amount INTEGER, note TEXT);
    """)
    conn.executemany(
        "INSERT INTO users VALUES (?,?,?)",
        [(i, f"user{i}", "x" * 500) for i in range(1, N_USERS + 1)],
    )
    conn.executemany(
        "INSERT INTO orders VALUES (?,?,?,?,?)",
        [(i, (i % N_USERS) + 1, f"item{i}", i * 100, "y" * 500)
         for i in range(1, N_ORDERS + 1)],
    )
    conn.commit()
    return conn


def demo_n_plus_1(conn: sqlite3.Connection) -> None:
    print("\n1) N+1 query — ดึงออเดอร์ 500 รายการพร้อมชื่อเจ้าของ")

    with timed("❌ N+1  (1 query + 500 query ในลูป)") as t1:
        rows = conn.execute(
            "SELECT id, user_id, item FROM orders LIMIT 500").fetchall()
        result = []
        for oid, uid, item in rows:                       # ← ตรงนี้คือปัญหา
            name = conn.execute(
                "SELECT name FROM users WHERE id = ?", (uid,)).fetchone()[0]
            result.append((oid, item, name))

    with timed("✅ JOIN  (query เดียว)") as t2:
        result2 = conn.execute("""
            SELECT o.id, o.item, u.name
            FROM orders o JOIN users u ON u.id = o.user_id
            LIMIT 500
        """).fetchall()

    assert len(result) == len(result2) == 500
    print(f"  → JOIN เร็วกว่า {t1.ms / t2.ms:.1f} เท่า")
    print("     บน sqlite ในหน่วยความจำยังต่างขนาดนี้")
    print("     ของจริงที่ DB อยู่คนละเครื่อง แต่ละ query มี network latency ~1ms")
    print(f"     → 500 query = ช้าเพิ่มอีกราว {500 * 1:.0f} ms")


def demo_index(conn: sqlite3.Connection) -> None:
    print("\n2) Index — ค้นออเดอร์ของ user คนหนึ่ง (ทำ 200 ครั้ง)")

    with timed("❌ ไม่มี index (full table scan)") as t1:
        for uid in range(1, 201):
            conn.execute(
                "SELECT id FROM orders WHERE user_id = ?", (uid,)).fetchall()

    conn.execute("CREATE INDEX idx_orders_user ON orders(user_id)")

    with timed("✅ มี index") as t2:
        for uid in range(1, 201):
            conn.execute(
                "SELECT id FROM orders WHERE user_id = ?", (uid,)).fetchall()

    print(f"  → เร็วกว่า {t1.ms / t2.ms:.1f} เท่า")

    # EXPLAIN QUERY PLAN บอกว่า DB ตัดสินใจใช้ index หรือ scan
    plan = conn.execute(
        "EXPLAIN QUERY PLAN SELECT id FROM orders WHERE user_id = 5").fetchall()
    print(f"     query plan: {plan[0][-1]}")


def demo_select_star(conn: sqlite3.Connection) -> None:
    print("\n3) SELECT * — ดึงคอลัมน์ที่ไม่ได้ใช้ (note ยาว 500 ตัวอักษร)")

    with timed("❌ SELECT *") as t1:
        conn.execute("SELECT * FROM orders LIMIT 5000").fetchall()

    with timed("✅ เลือกเฉพาะที่ใช้") as t2:
        conn.execute("SELECT id, item, amount FROM orders LIMIT 5000").fetchall()

    print(f"  → เร็วกว่า {t1.ms / t2.ms:.1f} เท่า และประหยัด bandwidth ของผู้ใช้ด้วย")


def main() -> None:
    print(f"สร้างข้อมูลจำลอง: users={N_USERS:,} orders={N_ORDERS:,}")
    conn = build_db()

    demo_n_plus_1(conn)
    demo_index(conn)
    demo_select_star(conn)

    print("""
สรุป
  N+1     เกิดจากการ query ในลูป — แก้ด้วย JOIN หรือ IN (...) ทีเดียว
  Index   ทุกคอลัมน์ที่ใช้ใน WHERE / ORDER BY / JOIN ควรมี index
  SELECT * ดึงเท่าที่ใช้ ทั้งเร็วกว่าและประหยัดเน็ตผู้ใช้มือถือ

ลองต่อ: เปลี่ยน N_ORDERS เป็น 500_000 แล้วรันใหม่
        ดูว่าอันไหน "ช้าขึ้นเป็นเส้นตรง" และอันไหน "แทบไม่ช้าขึ้นเลย"
""")
    conn.close()


if __name__ == "__main__":
    main()
