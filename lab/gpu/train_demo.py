#!/usr/bin/env python3
"""lab บทที่ 66 — วัดหน่วยความจำและความเร็วของการเทรนจริง

    python3 lab/gpu/train_demo.py

วัด 4 อย่างบน GPU ที่มี:
  1. training กิน VRAM มากกว่า inference กี่เท่า
  2. mixed precision (AMP) เร็วขึ้นแค่ไหน
  3. gradient checkpointing ประหยัด VRAM เมื่อ activation เด่น
  4. LoRA เทรนแค่กี่ % ของพารามิเตอร์
"""
import time
import torch
import torch.nn as nn
from torch.utils.checkpoint import checkpoint_sequential


def mib_peak():
    return torch.cuda.max_memory_allocated() / 1024**2


def section(t):
    print(f"\n=== {t} ===")


def main():
    if not torch.cuda.is_available():
        raise SystemExit("ต้องมี GPU")
    dev = "cuda"
    print(f"GPU: {torch.cuda.get_device_name(0)}  ·  torch {torch.__version__}")

    # 1. training vs inference ─────────────────────────────
    section("training กิน VRAM มากกว่า inference")
    torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()
    m = nn.Sequential(*[nn.Linear(4096, 4096) for _ in range(6)]).to(dev)
    w = torch.cuda.memory_allocated() / 1024**2
    x = torch.randn(256, 4096, device=dev)
    with torch.no_grad():
        m(x)
    torch.cuda.synchronize(); infer = mib_peak()
    torch.cuda.reset_peak_memory_stats()
    opt = torch.optim.Adam(m.parameters())
    (m(x) ** 2).mean().backward(); opt.step()
    torch.cuda.synchronize(); train = mib_peak()
    print(f"  น้ำหนักอย่างเดียว : {w:6.0f} MiB")
    print(f"  inference (peak)  : {infer:6.0f} MiB")
    print(f"  training  (peak)  : {train:6.0f} MiB  = {train/infer:.1f}x ของ inference")

    # 2. mixed precision ───────────────────────────────────
    section("mixed precision (AMP) เร็วขึ้นแค่ไหน")
    for use_amp in (False, True):
        torch.cuda.empty_cache()
        net = nn.Sequential(*[nn.Linear(4096, 4096) for _ in range(4)]).to(dev)
        opt = torch.optim.Adam(net.parameters())
        sc = torch.amp.GradScaler("cuda", enabled=use_amp)
        xb = torch.randn(512, 4096, device=dev)
        for _ in range(3):
            opt.zero_grad()
            with torch.autocast("cuda", enabled=use_amp):
                loss = (net(xb) ** 2).mean()
            sc.scale(loss).backward(); sc.step(opt); sc.update()
        torch.cuda.synchronize()
        t = time.perf_counter()
        for _ in range(20):
            opt.zero_grad()
            with torch.autocast("cuda", enabled=use_amp):
                loss = (net(xb) ** 2).mean()
            sc.scale(loss).backward(); sc.step(opt); sc.update()
        torch.cuda.synchronize()
        print(f"  {'AMP  ' if use_amp else 'fp32 '}: {(time.perf_counter()-t)/20*1000:6.1f} ms/step")

    # 3. gradient checkpointing (ตั้งให้ activation เด่น) ────
    section("gradient checkpointing (เมื่อ activation เด่น)")
    for ckpt in (False, True):
        torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()
        net = nn.Sequential(*[nn.Sequential(nn.Linear(1024, 1024), nn.GELU())
                              for _ in range(60)]).to(dev)
        xb = torch.randn(16384, 1024, device=dev, requires_grad=True)
        out = checkpoint_sequential(net, 10, xb, use_reentrant=False) if ckpt else net(xb)
        out.mean().backward()
        torch.cuda.synchronize()
        print(f"  {'เปิด ' if ckpt else 'ปิด  '}: peak {mib_peak():6.0f} MiB")

    # 4. LoRA ──────────────────────────────────────────────
    section("LoRA: เทรนแค่กี่ % ของพารามิเตอร์")
    full = 6 * 4096 * 4096
    for r in (4, 8, 16):
        lora = 6 * (4096 * r + r * 4096)
        print(f"  r={r:<3}: {lora:>12,} / {full:,} = {lora/full*100:.2f}%")


if __name__ == "__main__":
    main()
