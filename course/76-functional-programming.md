# บทที่ 76 · Functional Programming ภาคปฏิบัติ — เขียนโค้ดที่บั๊กน้อยลง

> [บทที่ 73](73-design-principles.md) บอกว่าโค้ดที่เทสต์ยากคือ design ที่แย่ **บทนี้แสดงว่า
> แนวคิด functional ทำให้โค้ดเทสต์ง่ายและบั๊กน้อยลงได้อย่างไร** — โดยไม่ต้อง
> เปลี่ยนภาษา ใช้ Python เดิม
>
> ทุกตัวอย่างวัด/รันจริงด้วย [lab/fp_demo.py](../lab/fp_demo.py)

## 76.1 แก่นของ FP — ไม่ใช่ภาษา แต่เป็นวิธีคิด {#s76-1}

```
Functional : ข้อมูลไม่เปลี่ยน · ฟังก์ชันไม่มีผลข้างเคียง · input เดิม → output เดิม
Imperative : แก้ค่าตัวแปร · มี state ที่เปลี่ยนไปเรื่อย ๆ
```

**ไม่ต้องใช้ Haskell** — เขียน Python แบบ functional ได้ และได้ประโยชน์หลัก
คือ **โค้ดที่คาดเดาได้และเทสต์ง่าย**

| แนวคิด FP | แปลว่า |
|---|---|
| **Pure function** | input เดิม → output เดิมเสมอ · ไม่แตะอะไรข้างนอก |
| **Immutability** | ข้อมูลสร้างแล้วไม่แก้ · เปลี่ยน = สร้างใหม่ |
| **No side effect** | ไม่แอบแก้ตัวแปรอื่น ไฟล์ ฐานข้อมูล ตอนคำนวณ |

## 76.2 ทำไม mutable state ทำให้บั๊ก — วัดจริง {#s76-2}

**บั๊กคลาสสิกที่ทุกคนโดน: mutable default argument**

```python
def add_item(item, basket=[]):        # ❌ list สร้างครั้งเดียว แชร์กันทุกการเรียก
    basket.append(item)
    return basket
```

รันจริง:

```
ตะกร้า A: ['apple']
ตะกร้า B: ['apple', 'banana']   ← ควรมีแค่ banana!
```

**ตะกร้าคนละใบกลับใช้ list เดียวกัน** — เพราะ `[]` ถูกสร้างตอน define ฟังก์ชัน
ครั้งเดียว ไม่ใช่ทุกครั้งที่เรียก นี่คือผลของ mutable state ที่ซ่อนอยู่

**บั๊กที่ร้ายกว่า: ฟังก์ชันแอบแก้ input**

```python
def apply_discount(order):            # ❌ แก้ของที่รับเข้ามา
    order["total"] *= 0.9
    return order
```

```
ราคาลด: 90.0
ต้นฉบับ: 90.0   ← ถูกแก้ไปด้วย! ทั้งที่ไม่ได้ตั้งใจ
```

**ต้นฉบับถูกแก้โดยไม่ได้ตั้งใจ** — โค้ดที่อื่นที่ถือ `order` ตัวนี้อยู่จะเจอค่า
เปลี่ยนไปแบบงง ๆ **นี่คือบั๊กที่ debug ยากที่สุดประเภทหนึ่ง** เพราะสาเหตุอยู่คนละที่
กับอาการ

## 76.3 Pure function แก้ทั้งหมด {#s76-3}

```python
def apply_discount(order):            # ✅ pure — สร้างใหม่ ไม่แตะ input
    return {**order, "total": order["total"] * 0.9}
```

```
pure — ลด: 90.0   ต้นฉบับ: 100   ← ไม่ถูกแตะ
```

**pure function ไม่แตะโลกภายนอก** — รับ input มา คืน output ใหม่ จบ ไม่มีใคร
ถูกแก้แบบไม่รู้ตัว

และมันเทสต์ง่ายด้วยเหตุผลเดียวกัน:

```python
def tax(price, rate): return price * (1 + rate)
assert tax(100, 0.07) == tax(100, 0.07) == 107.0    # ✅ เรียกกี่ครั้งก็เท่าเดิม
```

> ## นี่คือ Dependency Injection จาก[บทที่ 73.2](73-design-principles.md#s73-2) ในอีกมุม
>
> pure function เทสต์ได้เพราะ **ไม่พึ่งอะไรภายนอก (เวลา, สุ่ม, ฐานข้อมูล, state)**
> — input เดิมให้ output เดิมเสมอ จึงเขียน `assert` ได้
>
> **โค้ดที่เทสต์ยากมักเป็นโค้ดที่มี side effect** ซ่อนอยู่ FP กำจัดต้นตอ

## 76.4 แยก "คำนวณ" ออกจาก "ผลข้างเคียง" {#s76-4}

โปรแกรมจริงต้องมี side effect (เขียนฐานข้อมูล ส่งอีเมล) — **FP ไม่ได้ห้าม
แต่ให้แยกมันออกไปที่ขอบ**

```
❌ ปนกัน:
def process_order(order):
    total = calculate(order)      # คำนวณ
    db.save(total)                # side effect
    send_email(order.user)        # side effect
    return total

✅ แยกแกน pure ออกจากขอบ:
def calculate_order(order):       # pure — เทสต์ได้เต็มที่
    return {...}

def process_order(order):         # ขอบ — จัดการ side effect
    result = calculate_order(order)   # เรียก pure core
    db.save(result)
    send_email(order.user)
    return result
```

> **แกน pure ที่เทสต์ได้ + เปลือกบาง ๆ ที่ทำ side effect** — นี่คือหลักการเดียวกับ
> Hexagonal architecture ([บทที่ 74.3](74-software-architecture.md#s74-3)) แต่ในระดับฟังก์ชัน
> business logic ที่ pure เทสต์ได้โดยไม่ต้องมีฐานข้อมูล

## 76.5 เครื่องมือ functional ที่ Python มีให้ {#s76-5}

```python
# map / filter — แปลง/กรอง โดยไม่แก้ของเดิม
prices = [100, 200, 300]
with_tax = [p * 1.07 for p in prices]        # list comprehension (functional)
cheap = [p for p in prices if p < 250]

# ไม่แก้ list เดิม — สร้างใหม่เสมอ
sorted_new = sorted(prices)                   # ✅ คืน list ใหม่
# prices.sort()                               # ❌ แก้ของเดิม (mutate)

# reduce — ยุบเหลือค่าเดียว
from functools import reduce
total = reduce(lambda acc, p: acc + p, prices, 0)
```

| ทำ (functional) | แทน (imperative) |
|---|---|
| `[f(x) for x in xs]` | loop + append |
| `sorted(xs)` | `xs.sort()` (แก้ของเดิม) |
| `{**d, "k": v}` | `d["k"] = v` (แก้ของเดิม) |
| `tuple` / `frozenset` | list / set ที่แก้ได้ |

> **`sorted(xs)` vs `xs.sort()` คือความต่างที่เห็นบ่อยสุด** — ตัวแรกคืนของใหม่
> (functional) ตัวหลังแก้ของเดิม (mutate) เลือกตัวแรกเมื่อไม่อยากให้ของเดิมเปลี่ยน

## 76.6 ศัพท์ FP ที่จะได้ยินในวงการ {#s76-6}

รู้ไว้พอสื่อสารได้ — ไม่ต้องลงลึก

| คำ | คือ (แบบสั้นที่สุด) |
|---|---|
| **Higher-order function** | ฟังก์ชันที่รับ/คืนฟังก์ชัน (`map`, decorator) |
| **Closure** | ฟังก์ชันที่จำค่าจาก scope ที่มันเกิด |
| **Currying** | แยกฟังก์ชันหลาย arg เป็นทีละ arg |
| **Immutable** | เปลี่ยนไม่ได้ (`tuple`, `frozenset`, `str`) |
| **Lambda** | ฟังก์ชันไม่มีชื่อ (`lambda x: x+1`) |
| **Monad** | โครงห่อค่าพร้อม context (เช่น `Optional`, `Promise`) — ลึก ข้ามได้ |

> ## Monad — รู้แค่ว่ามันคืออะไรพอ
>
> คุณใช้แนวคิด monad อยู่แล้วโดยไม่รู้ตัว — `Optional`/`None` ที่ต้องเช็คก่อนใช้,
> `Promise`/`async` ที่ห่อค่าที่ยังไม่มา ([บทที่ 33](33-concurrency-and-async.md)) ล้วนมีโครงแบบ monad
>
> **สำหรับสาย practical รู้แค่นี้พอ** — การเข้าใจ Category Theory เต็มรูปเป็น
> การลงทุนใหญ่ที่ผลตอบแทนกระจาย เหมาะกับคนที่สนใจทฤษฎีเป็นพิเศษ ([บทที่ 75.7](75-computation-theory.md#s75-7))

## 76.7 อย่าเปลี่ยนเป็น FP ทุกอย่าง {#s76-7}

| ใช้ functional เมื่อ | ใช้ imperative เมื่อ |
|---|---|
| business logic / คำนวณ | loop ที่ต้องการ performance สูงสุด |
| อยากเทสต์ได้ง่าย | I/O, side effect (ต้องมีอยู่แล้ว) |
| งานที่ concurrency ([บทที่ 33](33-concurrency-and-async.md)) | โค้ดที่ทีมคุ้น imperative กว่า |

> **immutability มีต้นทุน** — สร้าง object ใหม่แทนการแก้ที่เดิม ใช้หน่วยความจำ/
> เวลามากกว่าในงานที่ทำซ้ำล้านรอบ (เช่น loop ร้อนใน[บทที่ 67](67-profiling.md)) **เลือกตาม
> บริบท** — pure สำหรับ logic ที่ต้องถูกต้องและเทสต์ได้ · imperative สำหรับ
> จุดที่ต้องเร็วที่สุด

**หลักที่เอาไปใช้ได้ทันทีโดยไม่ต้อง "เปลี่ยนเป็น FP":**

1. **ฟังก์ชันอย่าแก้ input** — สร้างใหม่แทน ([76.3](#s76-3))
2. **อย่าใช้ mutable default argument** ([76.2](#s76-2))
3. **แยก pure logic ออกจาก side effect** ([76.4](#s76-4))

สามข้อนี้ลดบั๊กได้มากโดยไม่ต้องรู้ทฤษฎีอะไรเลย

## แบบฝึกหัด

1. รัน [lab/fp_demo.py](../lab/fp_demo.py) — mutable default argument ทำ bug ยังไง
2. หาฟังก์ชันในโค้ดคุณที่แก้ input ที่รับเข้ามา ([76.2](#s76-2)) — เปลี่ยนเป็น pure
3. หา `def f(x, items=[])` ในโค้ดคุณ — มี bug ซ่อนไหม
4. แยกฟังก์ชันที่ปนคำนวณกับ side effect ออกเป็นสองส่วน ([76.4](#s76-4))
5. เปลี่ยน `list.sort()` ที่แก้ของเดิม เป็น `sorted()` ที่คืนของใหม่ตรงที่เหมาะ
6. ตอบตัวเอง: `@lru_cache` ([บทที่ 67](67-profiling.md)) ทำงานได้เพราะฟังก์ชันเป็น pure —
   ถ้าฟังก์ชันมี side effect จะเกิดอะไรขึ้นถ้า cache มัน
7. เขียนอธิบายให้เพื่อนฟังใน 2 ประโยคว่าทำไม pure function ถึงเทสต์ง่ายกว่า

***
[⬅ ทฤษฎีการคำนวณภาคปฏิบัติ](75-computation-theory.md) · [สารบัญ](../README.md) · [ออกแบบระบบจากศูนย์ ➡](77-system-design.md)
