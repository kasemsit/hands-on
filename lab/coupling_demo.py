#!/usr/bin/env python3
"""lab บทที่ 73 — coupling ทำให้เทสต์ไม่ได้ · DI แก้ได้

    python3 lab/coupling_demo.py
"""
import random


class OrderBad:
    """❌ ผูกแน่นกับของที่คุมไม่ได้ → เทสต์ไม่ได้"""
    def total_with_tax(self, price):
        rate = random.choice([0.07, 0.10])       # จำลอง external API ที่สุ่ม
        return price * (1 + rate)


class OrderGood:
    """✅ ฉีด dependency เข้ามา → เทสต์ได้"""
    def __init__(self, tax_provider):
        self.tax = tax_provider

    def total_with_tax(self, price):
        return price * (1 + self.tax.rate())


class FakeTax:
    def rate(self):
        return 0.07


if __name__ == "__main__":
    print("=== OrderBad — รัน 3 ครั้งได้ผลต่างกัน เทสต์ไม่ได้ ===")
    o = OrderBad()
    for _ in range(3):
        print(f"  {o.total_with_tax(100):.2f}")

    print("\n=== OrderGood(FakeTax) — ผลเดิมเป๊ะ ===")
    g = OrderGood(FakeTax())
    for _ in range(3):
        print(f"  {g.total_with_tax(100):.2f}")
    assert g.total_with_tax(100) == 107.0
    print("  ✅ assert 107.0 ผ่าน")
