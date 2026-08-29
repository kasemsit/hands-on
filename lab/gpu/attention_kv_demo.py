#!/usr/bin/env python3
"""lab บทที่ 78 — KV cache ของ attention แต่ละแบบ + MoE sparsity

    python3 lab/gpu/attention_kv_demo.py
"""
# KV cache ของ attention แต่ละแบบ — คำนวณจาก config จริง
def kv_bytes_per_token(layers, kv_heads, head_dim, dtype=2):
    return 2 * layers * kv_heads * head_dim * dtype   # 2 = K และ V

print("=== KV cache ต่อ token — MHA vs GQA vs MLA ===")
print(f"{'แบบ':<28}{'kv_heads':>10}{'bytes/tok':>12}{'@8k ctx':>12}")

# Llama-3 8B config จริง: 32 layers, 32 heads, head_dim 128
L, H, D = 32, 32, 128

# MHA: kv_heads = heads = 32
mha = kv_bytes_per_token(L, 32, D)
# GQA: Llama-3 ใช้ 8 kv_heads (แชร์ K/V)
gqa = kv_bytes_per_token(L, 8, D)
# MLA (DeepSeek style): บีบ KV เป็น latent ~512 dim ต่อ layer
mla = 2 * L * 512 * 2   # latent_dim 512

for name, kvh, b in [("MHA (kv_heads=32)", 32, mha),
                     ("GQA (kv_heads=8, Llama-3)", 8, gqa),
                     ("MLA (latent=512)", "-", mla)]:
    at8k = b * 8192 / 1024**2
    print(f"{name:<28}{str(kvh):>10}{b:>12}{at8k:>10.0f}MB")

print(f"\n  GQA เล็กกว่า MHA {mha/gqa:.0f} เท่า → รับคนได้ {mha/gqa:.0f} เท่า")
print(f"  MLA เล็กกว่า MHA {mha/mla:.1f} เท่า")

# MoE: sparsity
print("\n=== MoE — พารามิเตอร์ active vs total ===")
total_experts, active = 896, 16      # ตัวอย่างจาก job (16-of-896)
print(f"  {active}-of-{total_experts}: active แค่ {active/total_experts*100:.1f}% ของ expert")
print(f"  → คำนวณเท่า dense {active} expert แต่มีความรู้ของ {total_experts} expert")
