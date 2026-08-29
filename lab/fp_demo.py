#!/usr/bin/env python3
"""lab บทที่ 76 — bug จาก mutable state และ pure function

    python3 lab/fp_demo.py
"""
# ── 1. bug คลาสสิก: mutable default argument ──
print("=== mutable default argument — bug ที่ทุกคนโดน ===")
def add_item_bad(item, basket=[]):        # ❌ list ถูกสร้างครั้งเดียว แชร์กันทุกครั้ง
    basket.append(item)
    return basket
print(f"  ตะกร้า A: {add_item_bad('apple')}")
print(f"  ตะกร้า B: {add_item_bad('banana')}   ← ควรมีแค่ banana!")

def add_item_good(item, basket=None):     # ✅
    basket = list(basket) if basket else []
    basket.append(item)
    return basket
print(f"  แก้แล้ว A: {add_item_good('apple')}")
print(f"  แก้แล้ว B: {add_item_good('banana')}")

# ── 2. shared mutable state ทำ bug ที่ debug ยาก ──
print("\n=== แก้ของที่แชร์กัน = bug ที่ตามยาก ===")
def apply_discount_bad(order):            # ❌ แก้ input
    order["total"] *= 0.9
    return order
original = {"total": 100}
discounted = apply_discount_bad(original)
print(f"  ราคาลด: {discounted['total']}")
print(f"  ต้นฉบับ: {original['total']}   ← ถูกแก้ไปด้วย! (ไม่ได้ตั้งใจ)")

def apply_discount_good(order):           # ✅ pure — ไม่แตะ input
    return {**order, "total": order["total"] * 0.9}
orig2 = {"total": 100}
disc2 = apply_discount_good(orig2)
print(f"  pure — ลด: {disc2['total']}  ต้นฉบับ: {orig2['total']}   ← ไม่ถูกแตะ")

# ── 3. pure function เทสต์ได้เพราะ input เดิม = output เดิมเสมอ ──
print("\n=== pure function: input เดิม → output เดิมเสมอ ===")
def tax(price, rate): return price * (1 + rate)
print(f"  tax(100, 0.07) = {tax(100,0.07)} (เรียกกี่ครั้งก็เท่าเดิม)")
assert tax(100, 0.07) == tax(100, 0.07) == 107.0
print("  ✅ assert ผ่าน — เทสต์ได้เพราะไม่พึ่งอะไรภายนอก")
