#!/usr/bin/env python3
"""lab บทที่ 51 — พิสูจน์ว่า utilization.gpu หลอกตา

รัน 2 งานที่ประสิทธิภาพต่างกัน 100 เท่า
แต่ nvidia-smi รายงาน utilization ใกล้เคียงกันทั้งคู่

    python3 lab/gpu/utilization_demo.py
"""
import subprocess
import threading
import time

import torch


def sample_utilization(stop, out):
    """อ่าน utilization.gpu ทุก 50 ms ระหว่างที่งานกำลังรัน"""
    while not stop.is_set():
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,power.draw",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True)
        try:
            u, p = r.stdout.splitlines()[0].split(",")
            out.append((int(u), float(p)))
        except (ValueError, IndexError):
            pass
        time.sleep(0.05)


def measure(name, fn, seconds=4.0):
    """รัน fn ซ้ำ ๆ เป็นเวลา seconds แล้ววัด utilization กับ FLOPS"""
    fn()                                   # warm-up
    torch.cuda.synchronize()

    stop = threading.Event()
    samples = []
    t = threading.Thread(target=sample_utilization, args=(stop, samples))
    t.start()

    rounds, flops, t0 = 0, 0, time.perf_counter()
    while time.perf_counter() - t0 < seconds:
        flops += fn()
        rounds += 1
    torch.cuda.synchronize()
    dt = time.perf_counter() - t0

    stop.set()
    t.join()

    util = sum(s[0] for s in samples) / len(samples) if samples else 0
    power = sum(s[1] for s in samples) / len(samples) if samples else 0
    tflops = flops / dt / 1e12

    print(f"{name:<34} {util:>6.0f}%  {power:>7.0f}W  {tflops:>9.2f}  {rounds:>9,}")
    return tflops


def main():
    if not torch.cuda.is_available():
        raise SystemExit("ต้องมี GPU — ไม่พบ CUDA")

    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"PyTorch: {torch.__version__}\n")

    # งานที่ 1 — kernel จิ๋ว ยิงรัว ๆ  (GPU ยุ่งตลอด แต่แทบไม่ได้คำนวณอะไร)
    tiny = torch.randn(64, 64, device="cuda", dtype=torch.float16)

    def tiny_work():
        for _ in range(2000):         # ยิงถี่พอให้ GPU ไม่มีช่องว่าง
            tiny.add_(1.0)
        return 2000 * 64 * 64         # การบวก ≈ 1 flop ต่อค่า

    # งานที่ 2 — matmul ใหญ่  (ใช้ Tensor Core เต็มที่)
    big = torch.randn(8192, 8192, device="cuda", dtype=torch.float16)

    def big_work():
        torch.mm(big, big)
        return 2 * 8192 ** 3          # matmul = 2*N^3 flops

    print(f"{'งาน':<34} {'util':>6}  {'power':>7}  {'TFLOPS':>9}  {'รอบ':>9}")
    print("-" * 74)
    a = measure("① kernel จิ๋ว ยิงรัว ๆ", tiny_work)
    b = measure("② matmul 8192x8192 (fp16)", big_work)

    print("-" * 74)
    print(f"\nงานที่ ② คำนวณได้มากกว่างานที่ ① ถึง {b / a:,.0f} เท่า")
    print("แต่ utilization ต่างกันไม่ถึง 2 เท่า")
    print("\n→ utilization.gpu นับแค่ 'ช่วงเวลาที่มี kernel รันอยู่'")
    print("  ไม่ได้นับว่า kernel นั้นใช้ SM ไปกี่ตัว หรือคำนวณได้เท่าไร")
    print("  งาน ① ทำให้การ์ดยุ่งครึ่งเวลา โดยคำนวณได้แทบเป็นศูนย์")
    print("\n→ power draw เป็นตัวชี้ที่ดีกว่า — ต่างกันชัดเจนกว่า utilization")


if __name__ == "__main__":
    main()
