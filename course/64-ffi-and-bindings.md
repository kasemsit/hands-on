# บทที่ 64 · เรียกข้ามภาษา — FFI และการเขียน binding

> ทำไม numpy เขียนด้วย Python แต่เร็วกว่า Python loop หลายสิบเท่า
> ทำไม PyTorch สั่ง GPU ได้ทั้งที่คุณเขียนแต่ Python
>
> **คำตอบเดียวกัน: ข้างในมันเรียก C/C++/CUDA** — บทนี้อธิบายว่ากลไกนั้นทำงานอย่างไร
> และเขียนเองได้อย่างไร

## 64.1 ทำไมต้องเรียกข้ามภาษา {#s64-1}

```
Python : เขียนง่าย อ่านง่าย แต่ loop ช้า
C/C++  : เขียนยาก แต่เร็วและคุมหน่วยความจำได้
   ↓
เขียน logic ด้วย Python · ยกงานหนักไปให้ C
```

**นี่คือสถาปัตยกรรมของ data science ทั้งวงการ** — numpy, pandas, PyTorch,
scikit-learn ล้วนเป็น Python บาง ๆ ห่อ C/C++/Fortran ที่ทำงานจริง

| ต้องการ | ทำไม FFI ช่วย |
|---|---|
| เร่งส่วนที่ช้า | ยก loop ร้อนไปเขียน C |
| ใช้ library ที่มีแต่ภาษา C | ไม่ต้องเขียนใหม่ |
| **คุม GPU** | CUDA เป็น C — PyTorch ก็เรียกผ่าน FFI ([บทที่ 49.3](49-gpu-on-containers-and-k8s.md#s49-3)) |
| ใช้โค้ดเก่าที่พิสูจน์แล้ว | OpenSSL, SQLite ล้วนเป็น C |

**FFI** = Foreign Function Interface — วิธีที่ภาษาหนึ่งเรียกฟังก์ชันของอีกภาษา

## 64.2 ทำงานได้เพราะทุกภาษาลงมาที่ ABI เดียวกัน {#s64-2}

ทำไม Python เรียก C ได้ทั้งที่เป็นคนละภาษา — เพราะ**ตอนคอมไพล์แล้ว
ทุกอย่างเหลือแค่ machine code ที่ทำตาม ABI เดียวกัน**

```
Python  ─┐
C       ─┼─→  machine code  →  ABI (System V x86-64)
Rust    ─┘                      "argument ที่ 1 อยู่ใน rdi, ค่า return อยู่ใน rax"
```

**ABI** (Application Binary Interface) คือข้อตกลงว่า **argument วางที่ register
ไหน ค่า return อยู่ที่ไหน** — [บทที่ 63](63-reverse-engineering.md) เห็นแล้ว ([บทที่ 63.5](63-reverse-engineering.md#s63-5)): `rdi, rsi, rdx...` คือ
argument, `rax` คือค่า return

**ตราบใดที่ทั้งสองฝั่งตกลง ABI เดียวกัน ก็เรียกกันได้** — ภาษาต้นทางไม่สำคัญ
นี่คือเหตุผลที่ `.so` ที่คอมไพล์จาก C เรียกจาก Python, Rust, Go ได้หมด

## 64.3 library แบบ shared — `.so` {#s64-3}

FFI ส่วนใหญ่เรียกผ่าน **shared library** (`.so` บน Linux, `.dll` บน Windows,
`.dylib` บน macOS)

```c
// fast.c — ยกงานหนักมาไว้ที่นี่
#include <stdint.h>
#include <stddef.h>

int64_t sum_squares(const int64_t *arr, size_t n) {
    int64_t s = 0;
    for (size_t i = 0; i < n; i++) s += arr[i] * arr[i];
    return s;
}
```

```bash
gcc -O2 -shared -fPIC -o libfast.so fast.c
```

| flag | ทำไมต้องมี |
|---|---|
| `-shared` | สร้าง `.so` ไม่ใช่ executable |
| **`-fPIC`** | position-independent code — โหลดที่ไหนในหน่วยความจำก็ได้ |
| `-O2` | optimize (จุดประสงค์ทั้งหมดคือความเร็ว) |

นี่คือ `.so` แบบเดียวกับที่[บทที่ 49.3](49-gpu-on-containers-and-k8s.md#s49-3) พูดถึง (`libcuda.so`, `libvgpu.so`)
และแบบเดียวกับที่ `LD_PRELOAD` ใน[บทที่ 49](49-gpu-on-containers-and-k8s.md) ดักได้

## 64.4 เรียกจาก Python — `ctypes` (มากับ stdlib) {#s64-4}

```python
import ctypes

lib = ctypes.CDLL("./libfast.so")

# ⚠️ ต้องประกาศ type ให้ตรงต้นฉบับ C
lib.sum_squares.argtypes = [ctypes.POINTER(ctypes.c_int64), ctypes.c_size_t]
lib.sum_squares.restype  = ctypes.c_int64

data = list(range(1, 10_000_001))
arr = (ctypes.c_int64 * len(data))(*data)
print(lib.sum_squares(arr, len(data)))
```

วัดจริง (`make demo` ใน [lab/ffi/](../lab/ffi/)):

```
ผลตรงกัน : True
Python   :   239.8 ms
ผ่าน C   :     4.5 ms
เร็วขึ้น  :    53.5 เท่า
```

**งานเดียวกัน เร็วขึ้น 53 เท่า** เพราะ loop วิ่งใน C ไม่ใช่ Python — และนี่คือ
เหตุผลทั้งหมดที่ numpy มีอยู่

## 64.5 🔴 กับดักอันดับหนึ่ง — type ไม่ตรง ABI {#s64-5}

**บรรทัด `argtypes`/`restype` ไม่ใช่ของประดับ** ถ้าลืม ctypes จะเดาว่าทุกอย่าง
เป็น `int` 32-bit

```python
lib_bad = ctypes.CDLL("./libfast.so")     # ไม่ประกาศ restype
result = lib_bad.sum_squares(arr, n)
```

ผลจริง:

```
ค่าถูก              : 333338333350000
ลืมประกาศ restype   : 1626540144        ← เพี้ยน (ถูกตัดเหลือ 32-bit)
โปรแกรมไม่ crash — แค่ได้คำตอบผิดเงียบ ๆ
```

> ## นี่คือบั๊กที่อันตรายที่สุดของ FFI
>
> **มันไม่ crash มันแค่ได้คำตอบผิด** — ค่า 64-bit ถูกตัดเหลือ 32-bit เงียบ ๆ
>
> ต่างจากบั๊กปกติที่โปรแกรมพังให้เห็น บั๊ก ABI ให้ตัวเลขที่ดู "เกือบถูก"
> ออกมา แล้วคุณเอาไปใช้ต่อโดยไม่รู้ตัว
>
> **เพราะไม่มีใครตรวจสอบให้** — Python เชื่อคุณว่าประกาศ type ถูก, C เชื่อว่า
> คนเรียกส่ง type ถูก ไม่มีใครเช็คตรงรอยต่อ นี่คือราคาของการข้ามภาษา

**pointer ที่ผิดร้ายกว่านั้น** — ถ้าส่ง pointer ผิด type อาจได้ segfault
หรือแก้หน่วยความจำผิดที่ (memory corruption — [บทที่ 37](37-memory-and-classic-exploits.md))

## 64.6 เครื่องมือแต่ละระดับ {#s64-6}

| เครื่องมือ | ภาษา | เหมาะกับ |
|---|---|---|
| **ctypes** | Python (stdlib) | เรียก `.so` ที่มีอยู่แล้ว เร็ว ๆ · ไม่ต้อง build |
| **cffi** | Python | เขียน binding จริงจัง · อ่าน header C ได้ |
| **pybind11** | C++ | ห่อ C++ (class, template) ให้ Python |
| **Cython** | Python-ish | เขียน Python ที่คอมไพล์เป็น C |
| **PyO3** | Rust | ห่อ Rust ให้ Python (นิยมขึ้นเรื่อย ๆ) |

> **เลือกอย่างไร**
>
> - มี `.so` อยู่แล้ว อยากเรียกเร็ว ๆ → **ctypes** (ไม่ต้องคอมไพล์อะไรเพิ่ม)
> - เขียน library ใหม่เพื่อแจก → **pybind11** (C++) หรือ **PyO3** (Rust)
> - แค่อยากให้ Python เดิมเร็วขึ้น → **Cython** หรือเขียน C แล้ว ctypes
>
> **numpy/PyTorch ใช้ทั้งหมดนี้ผสมกัน** — ไม่มีคำตอบเดียว

## 64.7 GIL — จุดที่ FFI ให้ของแถมสำคัญ {#s64-7}

Python มี **GIL** (Global Interpreter Lock) — โค้ด Python รันได้ทีละ thread
เท่านั้น ([บทที่ 33](33-concurrency-and-async.md)) ทำให้ multithreading ไม่เร่งงานที่ใช้ CPU หนัก

**แต่โค้ด C ปล่อย GIL ได้** — ระหว่างที่ C ทำงานหนัก thread อื่นของ Python
วิ่งต่อได้

```
Python loop 4 thread  →  ยังวิ่งทีละตัว (GIL)     → ไม่เร็วขึ้น
C ที่ปล่อย GIL 4 thread →  วิ่งขนานจริง            → เร็วขึ้นตามจำนวน core
```

**นี่คือเหตุผลที่ numpy บน array ใหญ่ใช้หลาย core ได้** ทั้งที่ Python ธรรมดา
ทำไม่ได้ — งานจริงอยู่ใน C ที่ปล่อย GIL แล้ว

> ⚠️ **แต่ถ้า C เรียก callback กลับมาที่ Python ต้องยึด GIL คืนก่อน** ไม่งั้น
> crash — เป็นจุดที่ binding เขียนผิดกันบ่อย

## 64.8 ความปลอดภัยของ binding {#s64-8}

การข้ามภาษา = ข้ามขอบเขตการตรวจสอบด้วย

| ความเสี่ยง | เพราะ |
|---|---|
| **โหลด `.so` ที่ถูกสับเปลี่ยน** | `LD_LIBRARY_PATH` ชี้ผิด → โหลด library ปลอม |
| ส่ง buffer เล็กเกิน | C ไม่เช็คขอบเขต → buffer overflow ([บทที่ 37](37-memory-and-classic-exploits.md)) |
| **pickle/`torch.load` เรียกโค้ด C** | RCE ตอน deserialize ([บทที่ 52.2](52-ai-system-security.md#s52-2)) |
| library เป็น dependency ที่ไม่ได้ตรวจ | supply chain ([บทที่ 42](42-supply-chain-security.md)) |

> **`.so` คือโค้ดที่รันด้วยสิทธิ์เต็มของ process** — ไม่มี sandbox ไม่มี
> memory safety ของ Python มาคุ้ม ต่างจากโค้ด Python ที่ผิดแล้วได้ exception
> โค้ด C ที่ผิดได้ memory corruption หรือ RCE
>
> **ตรวจ hash ของ `.so` ที่โหลด** ([บทที่ 42](42-supply-chain-security.md)) และอย่าโหลดจาก path ที่ผู้ใช้
> เขียนได้ — เหตุผลเดียวกับที่ `LD_PRELOAD` เป็นทั้งเครื่องมือและช่องโหว่
> ([บทที่ 49](49-gpu-on-containers-and-k8s.md))

## 64.9 สรุปเป็นภาพเดียว {#s64-9}

```
โค้ด Python ของคุณ
      │  ctypes / cffi / pybind11
      ▼
   .so (C/C++/Rust)   ← งานหนักอยู่ที่นี่ · ปล่อย GIL ได้
      │
      ▼
   ระบบ / GPU / library อื่น
```

**ทั้ง data science stack ที่คุณใช้ทุกวันคือรูปนี้** — เข้าใจมันแล้วจะ debug
ได้ลึกขึ้นเวลา `import` พัง, เวลา `.so` version ไม่ตรง, หรือเวลาต้องเร่งโค้ด
ที่ profiler บอกว่าช้า

## แบบฝึกหัด

1. `make demo` ใน [lab/ffi/](../lab/ffi/) — เครื่องคุณ C เร็วกว่า Python กี่เท่า
2. ลบบรรทัด `restype` ออกแล้วรันใหม่ — คำตอบเพี้ยนไหม เพี้ยนยังไง (ข้อ [64.5](#s64-5))
3. เขียนฟังก์ชัน C ที่รับ `double *` แล้วเรียกจาก Python — ประกาศ type ให้ถูก
4. ใช้ `ldd libfast.so` ดูว่ามันพึ่ง library อะไรบ้าง
5. ตอบตัวเอง: numpy ที่คุณใช้อยู่ ข้างในเป็นภาษาอะไร (`ลอง numpy.__config__.show()`)
6. หาโค้ด Python ของคุณที่ profiler บอกว่าช้า แล้วคิดว่าส่วนไหนควรยกไป C
7. ตอบตัวเอง: ถ้า `.so` ที่ import ถูกสับเปลี่ยน คุณจะรู้ได้อย่างไร (ข้อ [64.8](#s64-8))

***
[⬅ Reverse engineering เบื้องต้น](63-reverse-engineering.md) · [สารบัญ](../README.md) · [Linking และ loading ➡](65-linking-and-loading.md)
