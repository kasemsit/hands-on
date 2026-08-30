# บทที่ 83 · GPU Kernel และ FlashAttention — ทำไมมันเร็ว

> [บทที่ 48](48-serving-llm.md), [51](51-gpu-observability-and-cost.md) ใช้ Tensor Core และ FlashAttention โดยถือว่ามันเร็ว
> **บทนี้เปิดฝาดูว่ามันเร็วเพราะอะไรจริง ๆ** — ในระดับที่อ่าน CUDA/Triton
> เข้าใจ และรู้ว่าจะ optimize ตรงไหน
>
> ทุกตัวเลขวัดจริงบน RTX 3090 ด้วย [lab/gpu/kernel_bench.py](../lab/gpu/kernel_bench.py)

## 83.1 Kernel คืออะไร {#s83-1}

```
kernel = ฟังก์ชันที่รันบน GPU · หลายพัน thread ทำงานเดียวกันพร้อมกัน
```

ทุกอย่างที่ GPU ทำคือ kernel — matmul, softmax, การบวก การเรียกแต่ละครั้งคือ
**kernel launch** ซึ่งมี overhead

| คำ | คือ |
|---|---|
| **Kernel** | โค้ดที่รันบน GPU |
| **Kernel launch** | การสั่งให้ GPU รัน kernel (มี overhead) |
| **CUDA** | ภาษา/แพลตฟอร์มเขียน kernel ของ NVIDIA |
| **Triton** | เขียน kernel แบบ Python-ish (ง่ายกว่า CUDA) |

## 83.2 Tensor Core vs CUDA Core — วัดจริง {#s83-2}

GPU สมัยใหม่มีหน่วยคำนวณ 2 แบบ ([บทที่ 46](46-gpu-101.md))

```
CUDA Core   : คำนวณทั่วไป · fp32
Tensor Core : ทำ matmul โดยเฉพาะ · fp16/bf16 · เร็วกว่ามาก
```

วัดจริง (matmul 4096×4096):

```
fp32 (CUDA core)  :  6.71 ms   20.5 TFLOPS
fp16 (Tensor core):  2.43 ms   56.7 TFLOPS
เร็วกว่า 2.8 เท่า
```

> ## นี่คือเหตุผลที่ mixed precision เร่งได้ ([บทที่ 66.3](66-training-and-finetuning.md#s66-3))
>
> **Tensor Core ทำงานเฉพาะ fp16/bf16** — ถ้าโค้ดใช้ fp32 มันวิ่งบน CUDA Core
> ที่ช้ากว่า 2.8 เท่า **การเปลี่ยนเป็น fp16 ไม่ใช่แค่ประหยัด VRAM แต่ปลดล็อก
> Tensor Core ด้วย**
>
> `TENSOR_ACTIVE` ต่ำใน DCGM ([บทที่ 51.2](51-gpu-observability-and-cost.md#s51-2)) = ยังไม่ได้ใช้ Tensor Core =
> ทิ้งความเร็วนี้ไป

## 83.3 Kernel fusion — ลดการอ่าน/เขียน memory {#s83-3}

decode ติด memory bandwidth ([บทที่ 48](48-serving-llm.md)) — **การลดจำนวนครั้งที่อ่าน/เขียน
VRAM คือกุญแจ**

```
❌ แยก op:  y = x*2       ← อ่าน x, เขียน y     (รอบ memory 1)
            y = y+1       ← อ่าน y, เขียน y     (รอบ memory 2)
            y = relu(y)   ← อ่าน y, เขียน y     (รอบ memory 3)

✅ fuse:    y = relu(x*2+1)  ← อ่าน x ครั้งเดียว ทำทั้งหมด เขียนครั้งเดียว
```

**fusion รวมหลาย op เป็น kernel เดียว** — อ่าน memory ครั้งเดียว ทำทุกอย่าง
ในนั้น แล้วเขียนกลับครั้งเดียว ลดการวิ่ง VRAM ซึ่งเป็นคอขวด

> **PyTorch compiler (`torch.compile`) ทำ fusion ให้อัตโนมัติ** — แต่การเขียน
> kernel เองด้วย Triton ทำได้ดีกว่าในเคสเฉพาะ นี่คือที่มาของ custom kernel
> ในงาน serving ที่ต้องรีดความเร็วทุกหยด

## 83.4 FlashAttention — online softmax คือหัวใจ {#s83-4}

**ปัญหาของ attention ปกติ: ต้องสร้าง matrix N×N (attention score) ทั้งก้อน
ใน VRAM** — context ยาว = matrix ระเบิด

**FlashAttention ไม่สร้าง matrix ทั้งก้อน — เดินทีละ block ด้วย online softmax**

วัดจริง (online softmax เทียบ softmax ปกติ):

```
ผลต่างสูงสุด: 0.00e+00
→ ✅ เท่ากัน (เดินทีละ block ได้ผลเดียวกับทั้งก้อน)
```

**กลไก online softmax** — คำนวณ softmax โดยไม่ต้องเห็นข้อมูลทั้งแถวพร้อมกัน:

```
เดินทีละ chunk:
  เก็บ running max (m) และ running sum (s)
  เจอ chunk ใหม่ → อัปเดต m, s โดยปรับ scale ของที่สะสมไว้
  → ได้ผลเท่ากับคำนวณทั้งก้อน แต่ไม่ต้องเก็บทั้งก้อน
```

> ## นี่คือความสวยงามของ FlashAttention
>
> **ผลลัพธ์เท่ากับ attention ปกติเป๊ะ (ผลต่าง 0)** แต่ไม่ต้องเก็บ matrix N×N —
> จึง**VRAM คงที่ไม่โตตาม N²** และเร็วขึ้นเพราะไม่ต้องวิ่ง VRAM เขียน/อ่าน
> matrix ยักษ์
>
> เป็นเหตุผลเดียวกับที่ linear attention ([บทที่ 78.4](78-llm-architecture-internals.md#s78-4)) ทำ context ยาวได้ —
> **หลีกเลี่ยงการเก็บอะไรที่โตตาม N²**

## 83.5 GEMM — matmul ที่ทุกอย่างลงเอย {#s83-5}

**GEMM** (General Matrix Multiply) คือ operation ที่ LLM ใช้เวลาส่วนใหญ่ไปกับมัน

```
attention = matmul (Q×K, score×V)
FFN       = matmul (x×W)
ทุก layer = matmul เป็นหลัก
```

| optimize GEMM | ทำอะไร |
|---|---|
| **Tensor Core** | ฮาร์ดแวร์ทำ matmul โดยเฉพาะ ([83.2](#s83-2)) |
| **tiling** | แบ่งเป็น block ให้พอดี cache/shared memory |
| **CUTLASS** | library GEMM ของ NVIDIA ที่ปรับแต่งได้ |

> **library อย่าง FlashInfer / FlashKDA / CUTLASS คือ GEMM/attention kernel
> ที่ปรับจูนมาสุด ๆ** — งาน serving ระดับลึกคือการเลือก/เขียน kernel เหล่านี้
> ให้ตรงกับฮาร์ดแวร์ (Hopper, Blackwell)

## 83.6 อ่าน CUDA/Triton ให้เป็น {#s83-6}

ไม่ต้องเขียนเก่ง แต่**อ่านออกและแก้ได้**คือทักษะจริง

```python
# Triton — เขียน kernel แบบ Python-ish (อ่านง่ายกว่า CUDA มาก)
@triton.jit
def add_kernel(x_ptr, y_ptr, out_ptr, n, BLOCK: tl.constexpr):
    pid = tl.program_id(0)                      # thread block ไหน
    offs = pid * BLOCK + tl.arange(0, BLOCK)    # index ที่รับผิดชอบ
    mask = offs < n
    x = tl.load(x_ptr + offs, mask=mask)        # อ่านจาก VRAM
    y = tl.load(y_ptr + offs, mask=mask)
    tl.store(out_ptr + offs, x + y, mask=mask)  # เขียนกลับ
```

| อ่านอะไร | ดูอะไร |
|---|---|
| `program_id` | thread block นี้ทำส่วนไหน |
| `tl.load` / `tl.store` | อ่าน/เขียน VRAM (จุดที่กิน bandwidth) |
| `BLOCK` | ขนาด block (จูน performance) |

> **Triton อ่านง่ายกว่า CUDA มาก** — เขียน Python-ish แต่ compile เป็น GPU kernel
> เริ่มอ่าน kernel ของ vLLM/FlashInfer จาก Triton ก่อน ([บทที่ 79.7](79-vllm-internals.md#s79-7) อ่าน source)

## 83.7 สรุป — จะ optimize ต้องรู้อะไร {#s83-7}

| อาการ | น่าจะติดที่ | ทำอะไร |
|---|---|---|
| Tensor Core ไม่ทำงาน | ใช้ fp32 | เปลี่ยนเป็น fp16/bf16 ([83.2](#s83-2)) |
| memory-bound (decode) | อ่าน/เขียน VRAM เยอะ | fusion ([83.3](#s83-3)) · FlashAttention |
| context ยาวแล้ว OOM | attention matrix N×N | FlashAttention ([83.4](#s83-4)) |
| GEMM ช้า | kernel ไม่ optimize | CUTLASS/FlashInfer ([83.5](#s83-5)) |

**วัดก่อนเสมอ** ([บทที่ 51](51-gpu-observability-and-cost.md), [67](67-profiling.md)) — Nsight Systems / `torch.profiler` บอกว่า
kernel ไหนกินเวลา แล้วค่อย optimize ตรงนั้น ไม่ใช่เดา

## แบบฝึกหัด

1. รัน [lab/gpu/kernel_bench.py](../lab/gpu/kernel_bench.py) — Tensor Core เร็วกว่า CUDA Core กี่เท่า
2. ยืนยันเองว่า online softmax ให้ผลเท่า softmax ปกติ ([83.4](#s83-4))
3. ลอง `torch.compile` กับโมเดลเล็ก — เร็วขึ้นไหม (fusion อัตโนมัติ)
4. เปิด `torch.profiler` แล้วดูว่า kernel ไหนกินเวลามากสุด
5. อ่าน Triton kernel ตัวอย่างในข้อ [83.6](#s83-6) — `tl.load`/`tl.store` คือจุดที่กิน bandwidth ตรงไหน
6. ตอบตัวเอง: ทำไม FlashAttention ถึงทำ context ยาวได้โดย VRAM ไม่ระเบิด ([83.4](#s83-4))
7. หา kernel ใน vllm-project/vllm ที่เขียนด้วย Triton — อ่านว่ามันทำอะไร

***
[⬅ วัดผล GPU และคิดต้นทุนให้เป็น](51-gpu-observability-and-cost.md) · [สารบัญ](../README.md) · [ความปลอดภัยของระบบ AI ➡](52-ai-system-security.md)
