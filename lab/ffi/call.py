#!/usr/bin/env python3
"""เรียก C library จาก Python ด้วย ctypes — บทที่ 64

รัน: make demo   (จะ build libfast.so ให้เอง)
"""
import ctypes
import random
import time

lib = ctypes.CDLL("./libfast.so")

# ⚠️ ต้องประกาศ type ให้ตรงกับต้นฉบับ C เสมอ — ไม่งั้นได้คำตอบผิดเงียบ ๆ
lib.sum_squares.argtypes = [ctypes.POINTER(ctypes.c_int64), ctypes.c_size_t]
lib.sum_squares.restype = ctypes.c_int64


def bench(n=10_000_000):
    data = [random.randint(1, 100) for _ in range(n)]

    t = time.perf_counter()
    py = sum(x * x for x in data)
    t_py = time.perf_counter() - t

    arr = (ctypes.c_int64 * n)(*data)
    t = time.perf_counter()
    c = lib.sum_squares(arr, n)
    t_c = time.perf_counter() - t

    print(f"  ผลตรงกัน : {py == c}")
    print(f"  Python   : {t_py*1000:7.1f} ms")
    print(f"  ผ่าน C   : {t_c*1000:7.1f} ms")
    print(f"  เร็วขึ้น  : {t_py/t_c:6.1f} เท่า")


def show_abi_trap():
    data = list(range(1, 100001))
    arr = (ctypes.c_int64 * len(data))(*data)
    correct = sum(x * x for x in data)

    bad = ctypes.CDLL("./libfast.so")       # ไม่ประกาศ restype
    print(f"\n  ค่าถูก              : {correct}")
    print(f"  ลืมประกาศ restype   : {bad.sum_squares(arr, len(data))}  ← เพี้ยน")
    print(f"  โปรแกรมไม่ crash แค่ได้คำตอบผิด")


if __name__ == "__main__":
    bench()
    show_abi_trap()
