#!/usr/bin/env python3
"""
สาธิตว่าทำไม batching ถึงเป็นหัวใจของการเสิร์ฟ LLM — lab ของบทที่ 48

คำถามที่ตอบ:
    ทำไมเสิร์ฟทีละคนถึงเปลือง GPU
    batch ใหญ่ขึ้นแล้วได้อะไร เสียอะไร
    ทำไม continuous batching ถึงดีกว่า static batching

ใช้:
    python3 lab/gpu/batching_demo.py               # ครบทุกการทดลอง
    python3 lab/gpu/batching_demo.py --quick       # เร็วขึ้น
"""

import argparse
import time

import torch

# ขนาดใกล้เคียงชั้นหนึ่งของโมเดล 7-8B
HIDDEN = 4096
FFN = 14336


def bench(fn, warmup=3, iters=10) -> float:
    """คืนเวลาเฉลี่ยต่อรอบ (วินาที)"""
    for _ in range(warmup):
        fn()
    torch.cuda.synchronize()
    t = time.perf_counter()
    for _ in range(iters):
        fn()
    torch.cuda.synchronize()
    return (time.perf_counter() - t) / iters


def demo_batching(dtype, iters):
    """
    จำลองการคำนวณหนึ่งชั้นของ transformer ที่ batch ขนาดต่าง ๆ

    ประเด็น: เวลาต่อรอบแทบไม่เพิ่มตาม batch จนถึงจุดหนึ่ง
    เพราะ GPU ยังใช้ core ไม่เต็มตอน batch เล็ก
    """
    print("\n  การทดลองที่ 1 — batch size มีผลกับ throughput แค่ไหน")
    print("  " + "─" * 66)
    print(f"  {'batch':>6}{'เวลา/รอบ':>13}{'throughput':>16}{'เทียบ batch=1':>16}")
    print("  " + "─" * 66)

    w1 = torch.randn(HIDDEN, FFN, device="cuda", dtype=dtype)
    w2 = torch.randn(FFN, HIDDEN, device="cuda", dtype=dtype)

    base = None
    for bs in [1, 2, 4, 8, 16, 32, 64, 128]:
        x = torch.randn(bs, HIDDEN, device="cuda", dtype=dtype)

        def step():
            h = torch.nn.functional.silu(x @ w1)
            return h @ w2

        try:
            sec = bench(step, iters=iters)
        except torch.cuda.OutOfMemoryError:
            print(f"  {bs:>6}{'OOM':>13}")
            torch.cuda.empty_cache()
            break

        thr = bs / sec                      # sequence ต่อวินาที
        if base is None:
            base = thr
        print(f"  {bs:>6}{sec*1000:>10.2f} ms{thr:>13.0f} seq/s{thr/base:>13.1f}×")

    del w1, w2
    torch.cuda.empty_cache()

    print("\n  → batch ใหญ่ขึ้น = ใช้ GPU คุ้มขึ้นมาก โดยเวลาต่อรอบเพิ่มไม่มาก")
    print("    นี่คือเหตุผลที่การเสิร์ฟทีละ request เป็นการเผา GPU ทิ้ง")


def demo_padding_waste(dtype, iters):
    """
    static batching ต้อง pad ทุก sequence ให้ยาวเท่ากัน
    ถ้าความยาวต่างกันมาก งานที่เสียไปกับ padding จะเยอะมาก
    """
    print("\n  การทดลองที่ 2 — ต้นทุนของ padding ใน static batching")
    print("  " + "─" * 66)

    w = torch.randn(HIDDEN, HIDDEN, device="cuda", dtype=dtype)
    batch = 16
    lengths = [128, 256, 128, 1024, 128, 512, 128, 2048,
               128, 256, 128, 384, 128, 128, 128, 4096]

    padded_len = max(lengths)
    real_tokens = sum(lengths)
    padded_tokens = padded_len * batch

    x_pad = torch.randn(padded_tokens, HIDDEN, device="cuda", dtype=dtype)
    x_real = torch.randn(real_tokens, HIDDEN, device="cuda", dtype=dtype)

    t_pad = bench(lambda: x_pad @ w, iters=iters)
    t_real = bench(lambda: x_real @ w, iters=iters)

    print(f"  {'ความยาวจริงรวม':<32}{real_tokens:>8,} tokens")
    print(f"  {'ยาวสุดในชุด':<32}{padded_len:>8,} tokens")
    print(f"  {'ต้อง pad เป็น':<32}{padded_tokens:>8,} tokens")
    print(f"  {'เสียเปล่า':<32}{padded_tokens-real_tokens:>8,} tokens"
          f"  ({100*(1-real_tokens/padded_tokens):.0f}%)")
    print()
    print(f"  {'เวลาเมื่อ pad':<32}{t_pad*1000:>8.2f} ms")
    print(f"  {'เวลาถ้าไม่ต้อง pad':<32}{t_real*1000:>8.2f} ms")
    print(f"  {'ช้ากว่า':<32}{t_pad/t_real:>8.1f}×")

    del w, x_pad, x_real
    torch.cuda.empty_cache()

    print("\n  → continuous batching แก้ปัญหานี้ ด้วยการไม่ pad")
    print("    แต่จัดคิวทีละ token แทน (บทที่ 48.5)")


def demo_dtype(iters):
    """Tensor Core ทำงานเมื่อใช้ dtype ที่เหมาะสม"""
    print("\n  การทดลองที่ 3 — dtype มีผลกับความเร็วแค่ไหน")
    print("  " + "─" * 66)
    print(f"  {'dtype':<10}{'เวลา':>12}{'TFLOPS':>12}{'VRAM':>12}{'เทียบ fp32':>14}")
    print("  " + "─" * 66)

    torch.backends.cuda.matmul.allow_tf32 = True
    n = 4096
    base = None
    for dt, name in [(torch.float32, "fp32"), (torch.float16, "fp16"),
                     (torch.bfloat16, "bf16")]:
        if dt == torch.bfloat16 and not torch.cuda.is_bf16_supported():
            print(f"  {name:<10}{'ไม่รองรับ':>12}")
            continue
        a = torch.randn(n, n, device="cuda", dtype=dt)
        b = torch.randn(n, n, device="cuda", dtype=dt)
        sec = bench(lambda: a @ b, iters=iters)
        tflops = 2 * n**3 / sec / 1e12
        vram = a.element_size() * a.nelement() / 1024**2
        if base is None:
            base = tflops
        print(f"  {name:<10}{sec*1000:>9.2f} ms{tflops:>11.1f}{vram:>9.0f} MB"
              f"{tflops/base:>12.1f}×")
        del a, b
        torch.cuda.empty_cache()

    print("\n  → fp16/bf16 เร็วกว่าเพราะใช้ Tensor Core และ VRAM ครึ่งเดียว")


def main() -> int:
    if not torch.cuda.is_available():
        print("ไม่พบ GPU — lab นี้ต้องใช้ CUDA")
        return 1

    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="รันน้อยรอบ เร็วขึ้น")
    args = ap.parse_args()
    iters = 3 if args.quick else 10

    p = torch.cuda.get_device_properties(0)
    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16

    print(f"\n  GPU: {p.name} · {p.total_memory/1024**3:.1f} GiB · {p.multi_processor_count} SM")
    print(f"  dtype ที่ใช้ทดลอง: {str(dtype).replace('torch.','')}")

    demo_batching(dtype, iters)
    demo_padding_waste(dtype, iters)
    demo_dtype(iters)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
