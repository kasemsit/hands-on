# บทที่ 66 · เทรนและ fine-tune ให้เป็น

> ส่วนที่ 8 สอน **serve** โมเดล ([บทที่ 48](48-serving-llm.md)) — บทนี้สอนอีกด้านที่คุณจะใช้บ่อยกว่า
> ถ้าเป็นสาย data science: **เทรนและปรับโมเดลให้พอดีกับ GPU ที่มี**
>
> ทุกตัวเลขในบทนี้วัดจริงบน RTX 3090 ด้วย [lab/gpu/train_demo.py](../lab/gpu/train_demo.py)

## 66.1 ทำไม training กิน VRAM กว่า inference หลายเท่า {#s66-1}

[บทที่ 47](47-gpu-memory-and-kv-cache.md) คำนวณ VRAM สำหรับ inference **แต่ training กินมากกว่านั้นมาก**
เพราะต้องเก็บของเพิ่มอีก 3 อย่าง

```
inference : น้ำหนัก + activation ชั่วคราว
training  : น้ำหนัก + gradient + optimizer state + activation ทุกชั้น (เก็บไว้ทำ backward)
```

วัดจริง — โมเดล 6 ชั้น น้ำหนัก 384 MiB:

```
น้ำหนักอย่างเดียว : 384 MiB
inference (peak)  : 405 MiB   ≈ เท่าน้ำหนัก
training  (peak)  : 1941 MiB  = 4.8x ของ inference
```

**training กิน ~5 เท่าของ inference** — และตัวคูณมาจากไหน:

| ส่วน | ขนาดเทียบน้ำหนัก | ทำไม |
|---|---|---|
| น้ำหนัก | 1× | ตัวโมเดล |
| gradient | 1× | ทุกน้ำหนักมี gradient คู่กัน |
| **optimizer state (Adam)** | **2×** | Adam เก็บ momentum + variance ต่อพารามิเตอร์ |
| activation | แปรผัน | เก็บ output ทุกชั้นไว้ทำ backward |

> ## นี่คือเหตุผลที่ "โหลดโมเดลได้ ไม่ได้แปลว่าเทรนได้"
>
> โมเดล 7B โหลด inference ใช้ ~14 GiB (fp16) **แต่ full fine-tune ต้องการ
> ~4-5 เท่า = 60-80 GiB** — เกินการ์ด 24 GiB ไปไกล
>
> นี่คือเหตุผลที่ LoRA ([66.5](#s66-5)) ถึงมีอยู่ และเป็นสิ่งแรกที่ต้องคำนวณ
> ก่อนวางแผนเทรน (ใช้ [vram_calc.py](../lab/gpu/vram_calc.py) เป็นจุดตั้งต้น)

**Adam กิน optimizer state 2 เท่าของน้ำหนัก** — ถ้าเปลี่ยนเป็น SGD ธรรมดา
ประหยัดตรงนี้ได้ แต่มักเทรนยากกว่า ทางสายกลางคือ 8-bit Adam (`bitsandbytes`)
ที่ลด state ลงเหลือ ~0.5 เท่า

## 66.2 loop เทรนที่ถูกต้อง {#s66-2}

```python
model.train()
for x, y in loader:
    x, y = x.to(dev), y.to(dev)
    opt.zero_grad()                 # 1. ล้าง gradient เก่า
    out = model(x)                  # 2. forward
    loss = loss_fn(out, y)          # 3. คำนวณ loss
    loss.backward()                 # 4. backward — คำนวณ gradient
    opt.step()                      # 5. อัปเดตน้ำหนัก
```

| ขั้น | ลืมแล้วเกิดอะไร |
|---|---|
| `zero_grad()` | 🔴 **gradient สะสมทับกัน** — loss เพี้ยน หาสาเหตุยากมาก |
| `model.train()` | dropout/batchnorm ทำงานผิดโหมด |
| `.to(dev)` | ข้อมูลอยู่ CPU โมเดลอยู่ GPU → error |
| `no_grad()` ตอน eval | เก็บ activation เปล่า ๆ เปลือง VRAM |

> **`zero_grad()` ที่ลืมคือบั๊กคลาสสิก** — PyTorch **สะสม** gradient โดยตั้งใจ
> (เพื่อทำ gradient accumulation ได้ — [66.4](#s66-4)) ถ้าไม่ล้างเอง มันบวกกันไปเรื่อย ๆ
> โมเดลจะเทรนเพี้ยนแบบที่ดูเผิน ๆ ไม่ออก

## 66.3 Mixed precision — ของฟรีที่ควรเปิดเสมอ {#s66-3}

คำนวณด้วย fp16/bf16 แทน fp32 ตรงที่ทำได้ ([บทที่ 48](48-serving-llm.md) เรื่อง dtype)

วัดจริง:

```
fp32 : 15.8 ms/step
AMP  : 11.8 ms/step        เร็วขึ้น ~1.3x
```

```python
scaler = torch.amp.GradScaler("cuda")
for x, y in loader:
    opt.zero_grad()
    with torch.autocast("cuda"):          # คำนวณส่วนที่ทำได้ด้วย fp16/bf16
        loss = loss_fn(model(x), y)
    scaler.scale(loss).backward()          # ป้องกัน gradient เล็กจนหาย (underflow)
    scaler.step(opt)
    scaler.update()
```

> ## ทำไมต้องมี GradScaler
>
> fp16 มีช่วงตัวเลขแคบ — **gradient ที่เล็กมากจะกลายเป็น 0** (underflow)
> แล้วโมเดลไม่เรียนรู้ `GradScaler` คูณ loss ให้ใหญ่ขึ้นก่อน backward
> แล้วหารกลับตอน `step` เพื่อให้ gradient อยู่ในช่วงที่ fp16 เก็บได้
>
> **bf16 ไม่ต้องใช้ scaler** เพราะช่วงตัวเลขกว้างเท่า fp32 (แค่ความละเอียดน้อยกว่า)
> — ถ้าการ์ดรองรับ (Ampere ขึ้นไป) ใช้ bf16 ง่ายกว่า

**ผลตอบแทนจริงมาจาก Tensor Core** ([บทที่ 51](51-gpu-observability-and-cost.md)) — บนงานที่เป็น matmul เยอะ ๆ
mixed precision เร่งได้มากกว่า 1.3 เท่าที่วัดได้จาก MLP เล็ก ๆ นี้

## 66.4 เทรนโมเดลใหญ่กว่าที่ VRAM รับได้ {#s66-4}

### Gradient accumulation — จำลอง batch ใหญ่ด้วย VRAM น้อย

```python
accum = 4                             # อยากได้ batch 128 แต่ใส่ได้ทีละ 32
for i, (x, y) in enumerate(loader):
    with torch.autocast("cuda"):
        loss = loss_fn(model(x), y) / accum    # หารเฉลี่ย
    scaler.scale(loss).backward()              # สะสม gradient (ไม่ zero_grad)
    if (i + 1) % accum == 0:
        scaler.step(opt); scaler.update()
        opt.zero_grad()                        # ล้างหลังอัปเดตจริง
```

**ได้ผลเทียบเท่า batch 128 โดยใช้ VRAM ของ batch 32** — แลกด้วยเวลาที่นานขึ้น
เพราะทำ forward/backward 4 ครั้งต่อการอัปเดตหนึ่งครั้ง

### Gradient checkpointing — แลกเวลาเพื่อ VRAM

ปกติ training เก็บ activation ทุกชั้นไว้ทำ backward — checkpointing **ทิ้ง
activation แล้วคำนวณใหม่ตอน backward** ประหยัด VRAM แลกกับเวลา

วัดจริง (60 ชั้น batch ใหญ่ ให้ activation เด่น):

```
checkpointing ปิด  : peak 9926 MiB
checkpointing เปิด : peak 4133 MiB      ประหยัด 58%
```

```python
from torch.utils.checkpoint import checkpoint_sequential
out = checkpoint_sequential(model, segments=10, input=x, use_reentrant=False)
```

> ## ⚠️ checkpointing ช่วยเฉพาะเมื่อ activation ครองพื้นที่
>
> ตอนทดลองครั้งแรกกับโมเดลที่ **น้ำหนักครองพื้นที่** checkpointing กลับทำให้
> VRAM **เพิ่มขึ้น** (จาก overhead) — ต้องเปลี่ยนเป็นโมเดลชั้นเยอะ batch ใหญ่
> ที่ activation เด่นก่อน ถึงเห็นผลประหยัด 58%
>
> **บทเรียน: รู้ก่อนว่าอะไรกิน VRAM (น้ำหนัก/activation/optimizer) แล้วค่อย
> เลือกเครื่องมือให้ตรง** — เปิด checkpointing มั่ว ๆ อาจแย่ลง
> (วิธีดู breakdown อยู่ใน[บทที่ 47.1](47-gpu-memory-and-kv-cache.md#s47-1))

## 66.5 LoRA — fine-tune โดยแตะพารามิเตอร์แค่เศษเสี้ยว {#s66-5}

แทนที่จะปรับน้ำหนักทั้งหมด LoRA **แช่แข็งน้ำหนักเดิม แล้วเทรนเมทริกซ์เล็ก ๆ
คู่หนึ่งเสริมเข้าไป**

```
W (4096×4096) แช่แข็ง  +  A(4096×r) × B(r×4096)  ที่เทรน
                            └── r = 8 เล็กมาก ──┘
```

วัดจริง — โมเดล 6 ชั้น 100M พารามิเตอร์:

```
r=4  :   196,608 / 100,663,296 = 0.20%
r=8  :   393,216 / 100,663,296 = 0.39%
r=16 :   786,432 / 100,663,296 = 0.78%
```

**เทรนแค่ 0.4% ของพารามิเตอร์ทั้งหมด** — และผลที่ตามมา:

| ได้อะไร | เพราะ |
|---|---|
| VRAM ลดฮวบ | gradient + optimizer state คิดแค่ 0.4% ([66.1](#s66-1)) |
| เทรนเร็วขึ้น | อัปเดตน้ำหนักน้อยลงมาก |
| เก็บผลเล็ก | LoRA adapter ไม่กี่ MB ต่องาน ไม่ต้องก๊อปโมเดลทั้งตัว |
| สลับงานได้ | โมเดลฐานตัวเดียว + adapter หลายตัว |

> **นี่คือเหตุผลที่ fine-tune LLM บนการ์ด 24 GiB ได้จริง** — full fine-tune
> 7B ต้องการ 60-80 GiB ([66.1](#s66-1)) แต่ LoRA ลด gradient+optimizer ลงเหลือ
> เศษเสี้ยว จนพอดีการ์ดใบเดียว
>
> **QLoRA** ไปไกลกว่านั้น — quantize น้ำหนักฐานเป็น 4-bit ([บทที่ 47.8](47-gpu-memory-and-kv-cache.md#s47-8))
> แล้วทำ LoRA ทับ ทำให้เทรน 7B บนการ์ด ~12 GiB ได้

## 66.6 ปัญหาการเทรนที่เจอบ่อย {#s66-6}

| อาการ | สาเหตุที่พบบ่อย |
|---|---|
| **loss = NaN** | learning rate สูงไป · lr warmup ไม่มี · fp16 overflow (ใช้ bf16) |
| loss ไม่ลด | lr ต่ำไป · ลืม `zero_grad` · ข้อมูลผิด |
| **CUDA out of memory** | batch ใหญ่ไป → accumulation ([66.4](#s66-4)) · checkpointing · LoRA |
| GPU util ต่ำ | ติด I/O ไม่ใช่ compute ([บทที่ 51.6](51-gpu-observability-and-cost.md#s51-6)) — data loader ช้า |
| เทรนได้ แต่ eval แย่ | overfitting · ลืม `model.eval()` ตอนวัด |
| ผลไม่ซ้ำเดิมแต่ละรอบ | ไม่ได้ตั้ง seed |

> **`loss = NaN` คือฝันร้ายที่พบบ่อยที่สุด** — เริ่มจากลด lr ครึ่งหนึ่ง
> ถ้ายังเป็น ให้เปลี่ยน fp16 → bf16 และเพิ่ม gradient clipping
> (`torch.nn.utils.clip_grad_norm_`) ก่อนโทษโมเดลหรือข้อมูล

**ตั้ง seed ให้ครบทุกที่** เพื่อให้ debug ได้:

```python
torch.manual_seed(0); torch.cuda.manual_seed_all(0)
import random, numpy as np
random.seed(0); np.random.seed(0)
```

## 66.7 checklist ก่อนเทรนจริง {#s66-7}

- [ ] คำนวณ VRAM ที่ต้องใช้ **× 5** จาก inference ก่อน ([66.1](#s66-1)) — พอไหม
- [ ] เปิด mixed precision (bf16 ถ้าการ์ดรองรับ) ([66.3](#s66-3))
- [ ] ถ้า VRAM ไม่พอ: LoRA → gradient checkpointing → accumulation ตามลำดับ
- [ ] ตั้ง seed ทุกที่
- [ ] **บันทึก checkpoint ระหว่างเทรน** — ไฟดับ/OOM แล้วไม่เสียทั้งหมด
- [ ] เฝ้า GPU util — ถ้าต่ำ แก้ data loader ไม่ใช่ซื้อการ์ด ([บทที่ 51.6](51-gpu-observability-and-cost.md#s51-6))
- [ ] stage dataset ลง NVMe ถ้าอ่านจาก NFS ช้า ([บทที่ 51.6](51-gpu-observability-and-cost.md#s51-6))
- [ ] ยิงผ่านคิว (Slurm) ถ้าใช้คลัสเตอร์ร่วมกัน ([บทที่ 49.12](49-gpu-on-containers-and-k8s.md#s49-12))

## แบบฝึกหัด

1. รัน [train_demo.py](../lab/gpu/train_demo.py) บนการ์ดคุณ — training กิน VRAM
   กี่เท่าของ inference
2. เปิด/ปิด AMP แล้ววัดความเร็วบนงานที่เป็น matmul ล้วน — ต่างจาก 1.3x ไหม
3. หาค่า batch ที่ใหญ่ที่สุดที่การ์ดรับได้ แล้วใช้ accumulation จำลอง batch 4 เท่า
4. เปิด gradient checkpointing กับโมเดลที่ **น้ำหนักเด่น** — VRAM เพิ่มหรือลด
   ทำไม (ข้อ [66.4](#s66-4))
5. คำนวณ: full fine-tune Llama-3 8B ต้องการ VRAM เท่าไร แล้ว LoRA r=8 เหลือเท่าไร
6. จงใจตั้ง lr สูงจน loss = NaN แล้วแก้ทีละอย่างจนกลับมาปกติ (ข้อ [66.6](#s66-6))
7. ตอบตัวเอง: งานเทรนของคุณ ติด VRAM, ติด compute, หรือติด I/O
   — วัดก่อนตอบ

***
[⬅ Serving LLM ให้เป็น API](48-serving-llm.md) · [สารบัญ](../README.md) · [แบ่ง GPU ให้หลายคนใช้ ➡](49-gpu-on-containers-and-k8s.md)
