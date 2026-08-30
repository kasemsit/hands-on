#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lab บทที่ 83 — Tensor Core vs CUDA Core + online softmax

    python3 lab/gpu/kernel_bench.py
"""
import time

import torch


def bench(fn, n=50):
    for _ in range(3):
        fn()
    torch.cuda.synchronize()
    t = time.perf_counter()
    for _ in range(n):
        fn()
    torch.cuda.synchronize()
    return (time.perf_counter() - t) / n * 1000


def tensor_vs_cuda(dev):
    print("=== Tensor Core (fp16) vs CUDA Core (fp32) — matmul 4096 ===")
    a32 = torch.randn(4096, 4096, device=dev)
    b32 = torch.randn(4096, 4096, device=dev)
    a16, b16 = a32.half(), b32.half()
    t32 = bench(lambda: torch.mm(a32, b32))
    t16 = bench(lambda: torch.mm(a16, b16))
    flops = 2 * 4096 ** 3
    print(f"  fp32 (CUDA core)  : {t32:6.2f} ms  {flops/t32/1e9:6.1f} TFLOPS")
    print(f"  fp16 (Tensor core): {t16:6.2f} ms  {flops/t16/1e9:6.1f} TFLOPS")
    print(f"  เร็วกว่า {t32/t16:.1f} เท่า")


def online_softmax():
    """online softmax = แก่นของ FlashAttention — คำนวณทีละ chunk ไม่ต้องเก็บทั้งก้อน"""
    print("\n=== online softmax = แก่นของ FlashAttention ===")
    x = torch.randn(10000)

    def normal(x):
        e = torch.exp(x - x.max())
        return e / e.sum()

    def online(x, chunk=1000):
        m, s = float("-inf"), 0.0
        for i in range(0, len(x), chunk):
            c = x[i:i + chunk]
            new_m = max(m, c.max().item())
            s = s * torch.exp(torch.tensor(m - new_m)).item() + torch.exp(c - new_m).sum().item()
            m = new_m
        return torch.exp(x - m) / s

    a, b = normal(x), online(x)
    print(f"  ผลต่างสูงสุด: {(a - b).abs().max().item():.2e}")
    print(f"  → {'✅ เท่ากัน' if torch.allclose(a, b, atol=1e-6) else '❌ ต่าง'}"
          " (เดินทีละ block ได้ผลเดียวกับทั้งก้อน)")
    print("  ประโยชน์: attention ไม่ต้องเก็บ matrix N×N → VRAM ไม่โตตาม N²")


if __name__ == "__main__":
    if not torch.cuda.is_available():
        raise SystemExit("ต้องมี GPU")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    tensor_vs_cuda("cuda")
    online_softmax()
