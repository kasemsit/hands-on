# -*- coding: utf-8 -*-
"""lab บทที่ 85 — prefill/decode disaggregation, collective ops, EP

    python3 lab/gpu/parallel_demo.py
"""
# prefill vs decode มีลักษณะ compute ต่างกันมาก → แยกเครื่องได้ประโยชน์
print("=== prefill vs decode — ทำไมถึงแยกเครื่อง (disaggregation) ===")
print(f"{'':>10}{'compute':>14}{'ทำอะไร':>24}")
print(f"{'prefill':>10}{'หนัก (parallel)':>16}{'ประมวล prompt ทั้งก้อน':>26}")
print(f"{'decode':>10}{'เบา (ทีละ token)':>16}{'สร้างทีละตัว memory-bound':>26}")
print("\n  รวมเครื่องเดียว: prefill ของคนใหม่แย่ง compute จาก decode ของคนเก่า")
print("  → TTFT ดีขึ้น แต่ TPOT ของคนที่กำลัง decode สะดุด")
print("\n  แยกเครื่อง (disaggregation):")
print("    prefill node (การ์ดแรง compute) → ส่ง KV cache → decode node")
print("    → แต่ละงานได้เครื่องที่เหมาะ ไม่แย่งกัน")

# collective ops cost
print("\n=== collective ops — อันไหนแพงกว่า ===")
ops = [
    ("all-gather", "รวบทุก node ให้เห็นครบ", "N ข้อมูล"),
    ("reduce-scatter", "รวม+กระจายชิ้น", "N ข้อมูล"),
    ("all-reduce", "รวมทุก node แจกกลับ", "2N (= all-gather + reduce-scatter)"),
    ("all-to-all", "ทุก node แลกกับทุก node", "แพงสุด · ใช้ใน expert parallel"),
]
for name, what, cost in ops:
    print(f"  {name:<16}{what:<26}{cost}")

# EP: กระจาย expert ของ MoE
print("\n=== Expert Parallelism — กระจาย expert ของ MoE ===")
experts, gpus = 896, 8
print(f"  MoE {experts} expert · {gpus} GPU → {experts//gpus} expert/GPU")
print(f"  token ถูก route ไป expert ที่อาจอยู่คนละ GPU → ต้อง all-to-all")
print(f"  → นี่คือเหตุผลที่ MoE serve ยากกว่า dense (บทที่ 78.5)")
