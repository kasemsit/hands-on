#!/usr/bin/env python3
"""โปรแกรมที่ตั้งใจให้ช้า ไว้ฝึก profiler — บทที่ 67

    python3 -m cProfile -s tottime slow.py
"""
import functools


def fib(n):
    """recursion ซ้ำซ้อน — profiler จะชี้ว่าตรงนี้กินเวลาเกือบทั้งหมด"""
    return n if n < 2 else fib(n - 1) + fib(n - 2)


@functools.lru_cache(maxsize=None)
def fib_fast(n):
    """แก้แล้ว: memoize ด้วย lru_cache"""
    return n if n < 2 else fib_fast(n - 1) + fib_fast(n - 2)


def build_list(n):
    return [str(i) for i in range(n)]


def main():
    fib(30)               # ← กินเวลาส่วนใหญ่
    build_list(200_000)


if __name__ == "__main__":
    main()
