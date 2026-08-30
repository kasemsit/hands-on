# -*- coding: utf-8 -*-
"""lab บทที่ 84 — dtype range, fp16 overflow, int8 quantization

    python3 lab/gpu/quant_demo.py
"""
import torch
print("=== dtype: ช่วงตัวเลข vs ความละเอียด ===")
print(f"{'dtype':<10}{'bytes':>6}{'ช่วงสูงสุด':>16}{'หมายเหตุ':>20}")
for name, dt in [("fp32",torch.float32),("fp16",torch.float16),("bf16",torch.bfloat16)]:
    fi = torch.finfo(dt)
    print(f"{name:<10}{fi.bits//8:>6}{fi.max:>16.2e}   {'ละเอียดสูง' if name=='fp32' else ('ช่วงแคบ!' if name=='fp16' else 'ช่วงกว้างเท่า fp32')}")

print("\n=== ทำไม fp16 overflow แต่ bf16 ไม่ (บทที่ 66) ===")
big = torch.tensor(70000.0)
print(f"  ค่า 70000 ใน fp16: {big.half().item()}  ← inf! (เกินช่วง 65504)")
print(f"  ค่า 70000 ใน bf16: {big.bfloat16().item()}  ← ยังไหว (ช่วงเท่า fp32)")

print("\n=== quantization: น้ำหนักเล็กลง แต่ต้องมี scale ===")
# จำลอง int8 quantization ของ weight block
w = torch.randn(128) * 2.0
scale = w.abs().max() / 127          # map ช่วงจริงไป [-127,127]
q = torch.round(w / scale).clamp(-127,127).to(torch.int8)
deq = q.float() * scale              # แปลงกลับ
err = (w - deq).abs().mean().item()
print(f"  น้ำหนัก fp32: {w.numel()*4} bytes")
print(f"  int8 + scale: {w.numel()*1 + 4} bytes  (เล็กลง ~4 เท่า)")
print(f"  error เฉลี่ยหลังแปลงกลับ: {err:.4f}  (ยิ่ง block เล็ก error ยิ่งน้อย)")
