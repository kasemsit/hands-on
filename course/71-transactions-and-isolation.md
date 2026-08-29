# บทที่ 71 · Transaction และ Isolation — เมื่อหลายคนแก้ข้อมูลพร้อมกัน

> [บทที่ 27](27-database-and-performance.md) วัด N+1, index, connection pool **บทนี้ตอบคำถามที่ร้ายกว่า:
> เมื่อสอง request แก้แถวเดียวกันพร้อมกัน ข้อมูลจะเพี้ยนไหม**
>
> ทุกตัวเลขในบทนี้วัดจริงด้วย [lab/db_txn_demo.py](../lab/db_txn_demo.py) (sqlite ล้วน)

## 71.1 ปัญหาที่มองไม่เห็นจนกว่าจะโดน — lost update {#s71-1}

```python
# โอนเงิน: อ่าน → คิด → เขียน
bal = db.query("SELECT balance FROM account WHERE id=1")   # อ่าน 1000
new = bal - 100
db.execute("UPDATE account SET balance=?", new)            # เขียน 900
```

**ดูปกติทุกอย่าง — จนมีสอง request รันพร้อมกัน:**

```
เวลา   Request A            Request B
 t1    อ่าน bal = 1000
 t2                         อ่าน bal = 1000    ← เห็นค่าเก่า!
 t3    เขียน 900
 t4                         เขียน 900          ← ทับของ A
```

**ถอนไป 200 แต่ยอดลดแค่ 100** — เงิน 100 หายไปในอากาศ

วัดจริง (5 thread ถอนคนละ 100 ครั้ง):

```
=== ไม่มี transaction ===
  ควรเหลือ 500 · จริง 800  🔴 เงินหาย 300
```

**เงินหายจริง 300 บาท** — และตัวเลขนี้แกว่งทุกครั้งที่รัน เพราะขึ้นกับจังหวะ
ที่ thread ชนกัน (race condition — [บทที่ 33](33-concurrency-and-async.md))

## 71.2 ACID — สิ่งที่ transaction รับประกัน {#s71-2}

**transaction = กลุ่มคำสั่งที่ถือเป็นหน่วยเดียว** — สำเร็จทั้งหมดหรือไม่เกิดอะไรเลย

| ตัว | ย่อจาก | รับประกันว่า |
|---|---|---|
| **A** | Atomicity | ทำครบทุกคำสั่ง หรือไม่ทำเลย — ไม่มีครึ่ง ๆ |
| **C** | Consistency | ข้อมูลอยู่ในสถานะที่ถูกต้องตาม rule เสมอ |
| **I** | Isolation | transaction ที่รันพร้อมกันไม่กวนกัน |
| **D** | Durability | commit แล้วอยู่ถาวร แม้ไฟดับ |

```sql
BEGIN;
  UPDATE account SET balance = balance - 300 WHERE id = 1;
  UPDATE account SET balance = balance + 300 WHERE id = 2;
COMMIT;
```

**ถ้าระบบล่มหลังบรรทัดแรก atomicity คืนทุกอย่างกลับ** — ไม่มีกรณี "หักออก
แล้วแต่ยังไม่เข้า"

วัดจริง (จงใจ error กลางการโอน):

```
โอน 300 จากบัญชี 1 ไป 2 แล้ว error หลังหักออก → ROLLBACK
  บัญชี 1: 1000  บัญชี 2: 0  รวม: 1000
  → ✅ ไม่มีเงินหาย (rollback คืนทุกอย่าง)
```

## 71.3 แก้ lost update — atomic ที่ระดับฐานข้อมูล {#s71-3}

### วิธีที่ 1 — ล็อกตอนอ่าน

```sql
BEGIN IMMEDIATE;                                  -- ล็อกทันที กันคนอื่นเขียนแทรก
  SELECT balance FROM account WHERE id = 1;
  UPDATE account SET balance = ? WHERE id = 1;
COMMIT;
```

วัดจริง — โค้ดเดิม เพิ่มแค่ transaction:

```
=== BEGIN IMMEDIATE ===
  จริง 500  ✅ ตรง
```

**เพิ่มการล็อก เงินไม่หายอีกเลย**

### วิธีที่ 2 — ให้ฐานข้อมูลคำนวณเอง (ดีกว่า)

```sql
UPDATE account SET balance = balance - 100 WHERE id = 1;
```

**อ่าน-แก้-เขียนในคำสั่งเดียว** — ฐานข้อมูลรับประกัน atomic ให้เอง ไม่มีช่องให้
race เลย ถ้าทำได้ **ใช้วิธีนี้เสมอ** ดีกว่าอ่านมา Python แล้วเขียนกลับ

## 71.4 Isolation level — แลกความถูกต้องกับความเร็ว {#s71-4}

Isolation มีหลายระดับ — ยิ่งเข้ม ยิ่งถูกต้อง แต่ยิ่งช้า (ล็อกเยอะ)

| ระดับ | กันอะไรได้ | ปัญหาที่ยังเหลือ |
|---|---|---|
| **Read Uncommitted** | — | dirty read (อ่านของที่ยังไม่ commit) |
| **Read Committed** | dirty read | non-repeatable read |
| **Repeatable Read** | + non-repeatable | phantom read |
| **Serializable** | ทุกอย่าง | ช้าที่สุด · เหมือนรันทีละคน |

**อาการทั้งสามที่ต้องรู้จัก:**

| อาการ | คือ |
|---|---|
| **Dirty read** | อ่านข้อมูลที่อีก transaction ยังไม่ commit (อาจถูก rollback) |
| **Non-repeatable read** | อ่านแถวเดิมสองครั้งในระหว่าง transaction ได้ค่าต่างกัน |
| **Phantom read** | query เดิมได้จำนวนแถวต่างกัน (มีแถวใหม่โผล่) |

> ## ค่าเริ่มต้นของแต่ละฐานข้อมูลไม่เหมือนกัน
>
> | ฐานข้อมูล | default isolation |
> |---|---|
> | PostgreSQL, Oracle, SQL Server | **Read Committed** |
> | MySQL (InnoDB) | **Repeatable Read** |
>
> **โค้ดเดียวกันย้ายฐานข้อมูลแล้วพฤติกรรมต่างได้** เพราะ default ต่างกัน —
> เป็นบั๊กที่หาสาเหตุยากมาก ควรตั้ง isolation ให้ชัดในโค้ด ไม่พึ่ง default

## 71.5 Deadlock — สองฝ่ายรอกันวนไป {#s71-5}

```
Transaction A            Transaction B
ล็อกแถว 1                ล็อกแถว 2
ขอล็อกแถว 2 (รอ B)  ←──→  ขอล็อกแถว 1 (รอ A)
        └──── ต่างฝ่ายต่างรอ ไม่มีใครไปต่อ ────┘
```

**ฐานข้อมูลตรวจเจอ deadlock แล้วฆ่า transaction หนึ่งทิ้ง** (เลือกเหยื่อ) —
ฝั่งที่ถูกฆ่าได้ error ต้อง retry

| ป้องกัน | ทำอะไร |
|---|---|
| **ล็อกแถวตามลำดับเดียวกันเสมอ** | ทุก transaction ล็อก id น้อยก่อน → ไม่วนรอ |
| ทำ transaction ให้สั้น | ถือล็อกสั้นลง โอกาสชนน้อยลง |
| **retry เมื่อเจอ deadlock** | + exponential backoff ([บทที่ 56.4](56-background-jobs-and-queues.md#s56-4)) |

> **deadlock เป็นเรื่องปกติที่ต้องเผื่อไว้ ไม่ใช่บั๊กที่ต้องกำจัดให้หมด** —
> โค้ดที่ทำ transaction ต้องมี retry logic เสมอ

## 71.6 WAL — อ่านได้ขณะมีคนเขียน {#s71-6}

โดย default การเขียนล็อกไม่ให้ใครอ่าน **WAL (Write-Ahead Logging) แก้ปัญหานี้**

วัดจริง:

```
default : delete       ← เขียนล็อกการอ่าน
หลังเปิด: wal          ← อ่านได้ขณะเขียน
```

```sql
PRAGMA journal_mode = WAL;      -- sqlite
```

**WAL เก็บการเปลี่ยนแปลงในไฟล์แยกก่อน** แล้วค่อยรวมเข้าฐานหลัก — คนอ่านเห็น
เวอร์ชันเก่าที่ consistent ระหว่างที่คนเขียนทำงาน ทั้งคู่ไม่บล็อกกัน

PostgreSQL ใช้หลักการเดียวกัน (MVCC — Multi-Version Concurrency Control)
เป็น default อยู่แล้ว

## 71.7 optimistic vs pessimistic locking {#s71-7}

สองปรัชญาการจัดการการแก้พร้อมกัน

| | Pessimistic | Optimistic |
|---|---|---|
| แนวคิด | ล็อกไว้ก่อน กันคนอื่นแตะ | ไม่ล็อก · ตรวจตอนจะเขียนว่ามีคนแก้ไหม |
| เหมาะกับ | แก้ชนกันบ่อย | แก้ชนกันน้อย |
| กลไก | `SELECT ... FOR UPDATE` | version column / `WHERE version = ?` |

```sql
-- Optimistic: เขียนสำเร็จเฉพาะถ้า version ยังไม่เปลี่ยน
UPDATE doc SET content=?, version=version+1
WHERE id=? AND version=?;      -- ถ้าได้ 0 rows = มีคนแก้ไปแล้ว → retry
```

> **Optimistic locking คือหลักการเดียวกับ ETag** ใน[บทที่ 26](26-proxy-caching-cdn.md) และ
> refresh token rotation ใน[บทที่ 11](11-mobile-api-auth-design.md) — "ตรวจว่าของที่ฉันถืออยู่ยังใหม่ไหม
> ก่อนเขียนทับ" เป็น pattern ที่โผล่ซ้ำทั่วทั้งระบบ

## 71.8 checklist ก่อนเขียนโค้ดที่แก้ข้อมูลร่วมกัน {#s71-8}

- [ ] อ่าน-แก้-เขียน อยู่ใน transaction เดียว หรือใช้ `UPDATE ... SET x=x-1` ([71.3](#s71-3))
- [ ] transaction สั้นที่สุด — ไม่มี network call ค้างอยู่ข้างใน
- [ ] มี retry logic สำหรับ deadlock ([71.5](#s71-5))
- [ ] ตั้ง isolation level ชัดเจน ไม่พึ่ง default ([71.4](#s71-4))
- [ ] ล็อกแถวตามลำดับเดียวกันทุกที่ (กัน deadlock)
- [ ] เงิน/สต็อก/counter สำคัญ — ทดสอบด้วยการยิงพร้อมกันจริง ไม่ใช่ทีละครั้ง

> **ข้อสุดท้ายคือที่คนพลาดบ่อยที่สุด** — เทสต์ทีละ request จะผ่านหมด
> บั๊ก concurrency โผล่เฉพาะตอนยิงพร้อมกัน ([lab นี้](../lab/db_txn_demo.py) ใช้
> 5 thread เพื่อบังคับให้มันโผล่)

## แบบฝึกหัด

1. `python3 lab/db_txn_demo.py` — เงินหายเท่าไรบนเครื่องคุณ รันซ้ำ 3 ครั้ง
   ตัวเลขเท่ากันไหม ทำไม
2. เปลี่ยน `unsafe()` ให้ใช้ `UPDATE SET balance=balance-1` แทนการอ่านมาคิด
   — ยังหายไหม ([71.3](#s71-3) วิธีที่ 2)
3. เขียนโค้ดโอนเงินระหว่างสองบัญชีที่ทน error กลางคันได้ (atomicity)
4. หาว่าฐานข้อมูลที่คุณใช้ default isolation อะไร ([71.4](#s71-4))
5. จำลอง deadlock: สอง transaction ล็อกสองแถวสลับลำดับกัน — เกิดอะไรขึ้น
6. เปิด WAL บน sqlite แล้วลองอ่านขณะมีคนเขียน — บล็อกไหม
7. ตอบตัวเอง: โค้ดที่คุณเขียนมีตรงไหนที่อ่าน-แก้-เขียนโดยไม่มี transaction

***
[⬅ Database และ Performance ของ API](27-database-and-performance.md) · [สารบัญ](../README.md) · [Observability เจาะลึก ➡](68-observability-deep.md)
