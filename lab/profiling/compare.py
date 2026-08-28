#!/usr/bin/env python3
"""วัดผลก่อน/หลังแก้ตามที่ profiler ชี้ — บทที่ 67"""
import functools
import time


def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)


@functools.lru_cache(maxsize=None)
def fib_memo(n):
    return n if n < 2 else fib_memo(n - 1) + fib_memo(n - 2)


def bench(fn, *a):
    t = time.perf_counter()
    fn(*a)
    return (time.perf_counter() - t) * 1000


if __name__ == "__main__":
    a = bench(fib, 32)
    b = bench(fib_memo, 32)
    print(f"fib(32) ธรรมดา  : {a:8.2f} ms")
    print(f"fib(32) memoize : {b:8.4f} ms")
    print(f"เร็วขึ้น {a/b:,.0f} เท่า")
