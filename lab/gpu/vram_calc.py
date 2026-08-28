#!/usr/bin/env python3
"""
เครื่องคำนวณ VRAM สำหรับ LLM inference — lab ของบทที่ 47

ตอบคำถามที่คนทำ AI infrastructure โดนถามตลอด:
    "การ์ดใบนี้รันโมเดลนี้ได้ไหม"
    "เสิร์ฟพร้อมกันได้กี่คน"
    "ต้องซื้อการ์ดเพิ่มไหม"

ใช้:
    python3 lab/gpu/vram_calc.py                      # ดูตารางโมเดลยอดนิยม
    python3 lab/gpu/vram_calc.py --model llama3-8b    # เจาะโมเดลเดียว
    python3 lab/gpu/vram_calc.py --model llama3-8b --dtype int8 --ctx 8192

ตัวเลขที่ได้เป็นการประมาณที่ดีพอสำหรับการวางแผน
ของจริงจะต่างไปบ้างตาม kernel และ framework ที่ใช้
"""

import argparse
import subprocess
import sys
from dataclasses import dataclass

GIB = 1024 ** 3
MIB = 1024 ** 2

# ค่าใช้จ่ายคงที่ที่คนมักลืมนับ (วัดจริงบน RTX 3090 ได้ ~308 MiB)
CUDA_CONTEXT_MIB = 500          # CUDA context + cuBLAS/cuDNN kernel
FRAMEWORK_OVERHEAD_MIB = 500    # buffer ของ framework, fragmentation


@dataclass
class Model:
    name: str
    params_b: float       # พันล้านพารามิเตอร์
    layers: int
    hidden: int
    heads: int            # attention head ทั้งหมด
    kv_heads: int         # KV head (น้อยกว่า heads ถ้าใช้ GQA)

    @property
    def head_dim(self) -> int:
        return self.hidden // self.heads


# ค่าจากไฟล์ config ของแต่ละโมเดล
MODELS = {
    "llama3-8b":    Model("Llama-3 8B",       8.0,  32, 4096,  32,  8),
    "llama3-70b":   Model("Llama-3 70B",     70.0,  80, 8192,  64,  8),
    "qwen2.5-7b":   Model("Qwen2.5 7B",       7.6,  28, 3584,  28,  4),
    "qwen2.5-14b":  Model("Qwen2.5 14B",     14.8,  48, 5120,  40,  8),
    "mistral-7b":   Model("Mistral 7B",       7.2,  32, 4096,  32,  8),
    "gemma2-9b":    Model("Gemma 2 9B",       9.2,  42, 3584,  16,  8),
    "phi3-mini":    Model("Phi-3 mini 3.8B",  3.8,  32, 3072,  32, 32),
}

# byte ต่อค่าหนึ่งค่า
DTYPES = {"fp32": 4.0, "fp16": 2.0, "bf16": 2.0, "int8": 1.0, "int4": 0.5}


def weights_gib(m: Model, dtype: str) -> float:
    """หน่วยความจำที่น้ำหนักโมเดลกิน"""
    return m.params_b * 1e9 * DTYPES[dtype] / GIB


def kv_bytes_per_token(m: Model, kv_dtype: str) -> float:
    """
    KV cache ต่อ 1 token

        2 (K และ V) × layers × kv_heads × head_dim × bytes

    ตัวคูณ 2 มาจากที่ต้องเก็บทั้ง Key และ Value
    kv_heads ที่น้อยกว่า heads คือผลของ GQA (Grouped Query Attention)
    ซึ่งเป็นเหตุผลที่โมเดลใหม่ ๆ กิน KV cache น้อยกว่ารุ่นเก่ามาก
    """
    return 2 * m.layers * m.kv_heads * m.head_dim * DTYPES[kv_dtype]


def gpu_total_gib() -> float | None:
    """ถาม nvidia-smi ว่าการ์ดในเครื่องมี VRAM เท่าไร"""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip().split("\n")[0]
        return int(out) * MIB / GIB
    except Exception:
        return None


def report(m: Model, dtype: str, kv_dtype: str, ctx: int, vram_gib: float) -> None:
    w = weights_gib(m, dtype)
    overhead = (CUDA_CONTEXT_MIB + FRAMEWORK_OVERHEAD_MIB) * MIB / GIB
    kv_per_tok = kv_bytes_per_token(m, kv_dtype)
    kv_per_seq = kv_per_tok * ctx / GIB
    free = vram_gib - w - overhead

    print(f"\n  {m.name}  ·  น้ำหนัก {dtype}  ·  KV cache {kv_dtype}  ·  context {ctx:,}")
    print("  " + "─" * 62)
    print(f"  {'VRAM ทั้งหมด':<34} {vram_gib:8.2f} GiB")
    print(f"  {'− น้ำหนักโมเดล':<34} {w:8.2f} GiB")
    print(f"  {'− CUDA context + framework':<34} {overhead:8.2f} GiB")
    print(f"  {'= เหลือให้ KV cache':<34} {free:8.2f} GiB")
    print("  " + "─" * 62)
    print(f"  {'KV cache ต่อ 1 token':<34} {kv_per_tok/1024:8.1f} KiB")
    print(f"  {'KV cache ต่อ 1 sequence':<34} {kv_per_seq:8.2f} GiB")

    if free <= 0:
        print("\n  ✗ โหลดโมเดลไม่ได้เลย — น้ำหนักอย่างเดียวก็เกิน VRAM แล้ว")
        print("    ทางแก้: ลด dtype (int8/int4) · ใช้โมเดลเล็กลง · แบ่งหลาย GPU")
        return

    n = int(free / kv_per_seq)
    print(f"\n  → เสิร์ฟพร้อมกันได้ประมาณ  {n}  sequence ที่ context {ctx:,}")
    if n == 0:
        print("    ✗ ไม่พอแม้แต่ 1 sequence — ลด context หรือ quantize KV cache")
    elif n < 4:
        print("    ⚠ น้อยมาก — throughput จะต่ำ ลอง int8 หรือลด context")

    # ความยาว context สูงสุดถ้าเสิร์ฟทีละคน
    max_ctx = int(free * GIB / kv_per_tok)
    print(f"  → ถ้าเสิร์ฟทีละคน context ยาวสุดได้ประมาณ {max_ctx:,} tokens")


def table(vram_gib: float, dtype: str, kv_dtype: str, ctx: int) -> None:
    print(f"\n  VRAM {vram_gib:.1f} GiB · น้ำหนัก {dtype} · KV {kv_dtype} · context {ctx:,}\n")
    print(f"  {'โมเดล':<22}{'น้ำหนัก':>10}{'KV/token':>11}{'พร้อมกัน':>11}")
    print("  " + "─" * 54)
    for m in MODELS.values():
        w = weights_gib(m, dtype)
        free = vram_gib - w - (CUDA_CONTEXT_MIB + FRAMEWORK_OVERHEAD_MIB) * MIB / GIB
        kv = kv_bytes_per_token(m, kv_dtype)
        if free <= 0:
            n = "โหลดไม่ได้"
        else:
            n = str(int(free / (kv * ctx / GIB)))
        print(f"  {m.name:<22}{w:>8.1f} GiB{kv/1024:>9.0f} KiB{n:>11}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", choices=sorted(MODELS), help="เจาะโมเดลเดียว")
    ap.add_argument("--dtype", choices=sorted(DTYPES), default="fp16", help="ชนิดของน้ำหนัก")
    ap.add_argument("--kv-dtype", choices=sorted(DTYPES), default="fp16", help="ชนิดของ KV cache")
    ap.add_argument("--ctx", type=int, default=4096, help="ความยาว context")
    ap.add_argument("--vram", type=float, help="VRAM (GiB) — ไม่ใส่จะอ่านจากการ์ดในเครื่อง")
    args = ap.parse_args()

    vram = args.vram or gpu_total_gib()
    if vram is None:
        print("ไม่พบ GPU ในเครื่อง — ระบุด้วย --vram 24", file=sys.stderr)
        return 1

    if args.model:
        report(MODELS[args.model], args.dtype, args.kv_dtype, args.ctx, vram)
    else:
        table(vram, args.dtype, args.kv_dtype, args.ctx)
        print("\n  เจาะรายตัว: python3 lab/gpu/vram_calc.py --model llama3-8b")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
