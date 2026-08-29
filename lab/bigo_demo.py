#!/usr/bin/env python3
"""lab บทที่ 75 — Big-O แปลงเป็นเวลาจริงบนนาฬิกา

    python3 lab/bigo_demo.py

แสดงว่า complexity ที่ต่างกัน ทำให้ speedup โตขึ้นตามขนาด ไม่ใช่คงที่
"""
import time, random

def bench(fn, *a):
    t=time.perf_counter(); fn(*a); return (time.perf_counter()-t)*1000

# ── 1. list membership O(n) vs set O(1) ──
print("=== ค้นหาสมาชิก: list O(n) vs set O(1) ===")
print(f"{'ขนาด':>10} {'list (ms)':>12} {'set (ms)':>12} {'เร็วกว่า':>10}")
for n in [1000, 10000, 100000]:
    data_list = list(range(n))
    data_set = set(data_list)
    targets = [random.randint(0, n) for _ in range(1000)]
    tl = bench(lambda: [t in data_list for t in targets])
    ts = bench(lambda: [t in data_set for t in targets])
    print(f"{n:>10} {tl:>12.2f} {ts:>12.4f} {tl/ts:>9.0f}x")

# ── 2. O(n²) vs O(n log n) ──
print("\n=== หาคู่ที่ซ้ำ: O(n²) เทียบ O(n) ===")
print(f"{'ขนาด':>10} {'O(n²) (ms)':>14} {'O(n) (ms)':>12} {'เร็วกว่า':>10}")
def has_dup_slow(a):                       # O(n²)
    for i in range(len(a)):
        for j in range(i+1, len(a)):
            if a[i]==a[j]: return True
    return False
def has_dup_fast(a):                       # O(n)
    return len(set(a)) != len(a)
for n in [500, 1000, 2000]:
    a=list(range(n))                       # ไม่มีซ้ำ = worst case
    t1=bench(has_dup_slow, a)
    t2=bench(has_dup_fast, a)
    print(f"{n:>10} {t1:>14.2f} {t2:>12.4f} {t1/t2:>9.0f}x")
