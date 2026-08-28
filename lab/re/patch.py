#!/usr/bin/env python3
"""พลิก sete (0f 94 c0) เป็น setne (0f 95 c0) — กลับผลของ check() ด้วยการแก้ 1 ไบต์"""
data = bytearray(open("crackme", "rb").read())
i = data.find(bytes.fromhex("0f94c0"))
assert i != -1, "ไม่พบ sete — คอมไพล์ด้วย -O0 -no-pie หรือยัง"
print(f"  แก้ offset 0x{i+1:x}: 0x94 (sete) -> 0x95 (setne)")
data[i + 1] = 0x95
open("crackme_patched", "wb").write(data)
