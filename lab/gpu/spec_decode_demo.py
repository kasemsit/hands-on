# -*- coding: utf-8 -*-
"""lab บทที่ 80 — speculative decoding speedup ตาม acceptance rate

    python3 lab/gpu/spec_decode_demo.py
"""
def speedup(ar, k, draft_ratio=0.2):
    et = (1 - ar**(k+1)) / (1 - ar)
    return et / (1 + k * draft_ratio)

print("=== Speculative decoding — speedup ตาม acceptance rate ===")
print(f"{'acceptance':>12}{'ได้/รอบ':>12}{'speedup':>10}")
k = 4
for ar in [0.5, 0.7, 0.8, 0.9]:
    et = (1 - ar**(k+1)) / (1 - ar)
    print(f"{ar:>11.0%}{et:>11.2f}{speedup(ar,k):>9.2f}x")
print(f"\n(draft เดา {k} token/รอบ · draft ถูกกว่า target 5 เท่า)")
print(f"\ncoding (acc 0.9) เร็วกว่า creative (acc 0.5) = {speedup(0.9,k)/speedup(0.5,k):.1f} เท่า")
