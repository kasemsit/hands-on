# lab 63 — แกะและแก้ binary

โจทย์ฝึก reverse engineering ที่รันได้จริง ไม่ต้องมีเครื่องมือพิเศษ

```bash
make demo
```

## ไฟล์

| ไฟล์ | คืออะไร |
|------|---------|
| `crackme.c` | ต้นฉบับ — เช็ครหัสผ่าน `s3cr3t` |
| `patch.py` | แก้ 1 ไบต์ให้ตรรกะกลับด้าน |

## ทำเอง

```bash
gcc -O0 -no-pie -o crackme crackme.c

strings crackme | grep s3          # เจอรหัสตรง ๆ เพราะเป็น string ธรรมดา
objdump -d crackme | less          # อ่าน assembly ของ check()
gdb ./crackme                      # ตั้ง breakpoint ที่ strcmp
```

**ทำในเครื่องตัวเองหรือ VM เท่านั้น — อย่าแกะซอฟต์แวร์ของคนอื่นโดยไม่มีสิทธิ์ (บทที่ 22)**
