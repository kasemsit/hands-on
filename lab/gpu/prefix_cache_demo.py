#!/usr/bin/env python3
"""lab บทที่ 79 — prefix caching และ PagedAttention fragmentation

    python3 lab/gpu/prefix_cache_demo.py
"""
# Prefix caching: บทสนทนาที่ prompt เดิมซ้ำ ไม่ต้อง prefill ใหม่
def prefill_saved(system_prompt_tokens, n_turns, avg_user_tokens):
    # ทุก turn ใน chat ส่ง history ทั้งหมดกลับมา → prefill ซ้ำ
    without = 0
    with_cache = 0
    history = system_prompt_tokens
    for turn in range(1, n_turns+1):
        without += history                      # prefill ทั้ง history ทุก turn
        with_cache += avg_user_tokens           # cache: prefill แค่ส่วนใหม่
        history += avg_user_tokens
    return without, with_cache

print("=== Prefix caching — chat ที่ system prompt + history ซ้ำ ===")
print(f"{'turn':>6}{'ไม่มี cache':>16}{'มี cache':>14}{'ประหยัด':>10}")
sys_tok = 500      # system prompt ยาว
for n in [5, 10, 20]:
    wo, wc = prefill_saved(sys_tok, n, 100)
    print(f"{n:>6}{wo:>14} tok{wc:>12} tok{(1-wc/wo)*100:>8.0f}%")

print("\n=== PagedAttention: fragmentation ===")
# แบบเก่า: จอง KV cache แบบต่อเนื่องตาม max_len → เสียเปล่า
max_len, actual = 2048, 300
print(f"  จองแบบ contiguous (max {max_len}): ใช้จริง {actual} → เสีย {(1-actual/max_len)*100:.0f}%")
# PagedAttention: จองเป็น block เล็ก ๆ ตามใช้จริง
block = 16
blocks_needed = -(-actual // block)   # ceil
print(f"  PagedAttention (block {block}): จอง {blocks_needed} block = {blocks_needed*block} tok → เสีย {(blocks_needed*block-actual)/(blocks_needed*block)*100:.0f}%")
