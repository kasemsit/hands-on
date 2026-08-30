# -*- coding: utf-8 -*-
"""lab บทที่ 82 — debug คะแนน eval: ผิดจริง vs โดนตัด

    python3 lab/eval_debug_demo.py
"""
# debug คะแนน: ตอบผิดจริง หรือแค่ถูกตัดกลางคัน
cases = [
    ("What is 15*23?", "345", "The answer is 345", "finished"),
    ("What is 15*23?", "345", "Let me calculate: 15*23 = 15*20 + 15*3 = 300 +", "length"),
    ("What is 12*12?", "144", "The answer is 143", "finished"),
]
print("=== debug คะแนน eval: แยก 'ผิดจริง' ออกจาก 'โดนตัด' ===")
print(f"{'expected':>10}{'got':>8}{'finish':>10}  วินิจฉัย")
for q, exp, out, finish in cases:
    got = exp in out
    if got:
        diag = "✅ ถูก"
    elif finish == "length":
        diag = "⚠️ โดนตัด! (เพิ่ม max_tokens ไม่ใช่โทษโมเดล)"
    else:
        diag = "🔴 ตอบผิดจริง"
    ans = exp if got else "?"
    print(f"{exp:>10}{ans:>8}{finish:>10}  {diag}")

print("\n=== benchmark แต่ละตัววัดอะไร ===")
for name, what in [("GSM8K","เลข/reasoning ระดับประถม"),
                   ("GPQA-Diamond","วิทยาศาสตร์ระดับปริญญาเอก"),
                   ("OCRBench","อ่านตัวอักษรจากภาพ"),
                   ("MMMU","เข้าใจภาพ+ข้อความหลายสาขา")]:
    print(f"  {name:<16}{what}")
