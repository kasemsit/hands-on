# CLAUDE.md

หนังสือสอน HTTP → API → ความปลอดภัย → GPU/AI infrastructure (53 บท ภาษาไทย)
สร้างเว็บด้วย **Quarto** · lab รันได้จริงบนเครื่องผู้อ่าน

## คำสั่งหลัก

```bash
make preview      # เปิด quarto preview (พอร์ต 4200)
make web          # สร้าง HTML อย่างเดียว → _book/
make all          # HTML + PDF + EPUB
make check        # ตรวจ mermaid ทุกบล็อกด้วย headless Chrome
make lab          # เปิด lab server (127.0.0.1:8080)
pytest -q         # 22 test + 2 xfail (สคริปต์ copy server.py ไปพอร์ต 8099)
```

## กับดักที่แลกมาด้วยการ debug จริง — อย่าเดินซ้ำ

1. **Quarto ไม่ render ` ```mermaid ` ธรรมดาให้** — มันโหลด mermaid.js เฉพาะ
   executable cell (` ```{mermaid} ` ใน `.qmd`) เท่านั้น เราแก้ด้วย
   `assets/mermaid/init.html` ที่โหลด mermaid.js ของ Quarto เองแล้วแปลง
   `pre.mermaid` → `div.mermaid-live` + re-render ตอนสลับธีม
   → **ห้ามลบไฟล์นี้** และ **ห้ามตรวจด้วยการ grep หา `class="mermaid"`**
   (นั่นคือ class ของ syntax highlight ไม่ได้แปลว่า render ได้ — เคยหลงมาแล้ว)
   ตรวจของจริงด้วย `make check` เท่านั้น
2. **`;` ใน mermaid ทำให้ parse พัง** เช่น `Set-Cookie: sid=abc; Path=/`
   → ต้อง escape เป็น `#59;`
3. **`Note over C:` ข้อความล้นกล่อง** → ใช้ `Note over C,S:` ให้กินสองคอลัมน์
4. **`<b>` ใช้ไม่ได้ใน note ของ sequence diagram** (ได้เฉพาะ flowchart ที่เปิด htmlLabels)
5. **`---` ปิดท้ายบทถูก Quarto อ่านเป็น YAML front matter** → ใช้ `***` แทนทุกที่
6. **`number-sections: false` ห้ามเปลี่ยน** — ทั้งเล่มอ้างอิงหัวข้อด้วยเลขที่พิมพ์เอง
   (เช่น "ดูข้อ 49.3") ถ้าเปิด auto-number เลขจะเพี้ยนทั้งเล่มเงียบ ๆ
7. **เลขบท = ชื่อเรียกถาวร ไม่ใช่ลำดับการอ่าน** — ลำดับอยู่ใน `_quarto.yml`
   อย่าเปลี่ยนชื่อไฟล์เพื่อจัดลำดับ จะพัง cross-reference 300 กว่าจุด
8. **PDF: lualatex พังกับภาษาไทย** (`selnolig.lua: bad argument`) → ใช้ `xelatex`
   และไม่มีฟอนต์ monospace ตัวไหนมีทั้งไทยและ box-drawing → `pdf-symbols.lua`
   แปลงอักขระกรอบเป็น ASCII เฉพาะตอนทำ PDF
9. **`quarto render --to pdf` ลบ HTML ที่สร้างไว้ทิ้ง** (Quarto ล้าง output dir)
   → ถ้าต้องการทั้งคู่ใช้ `quarto render` เปล่า ๆ หรือ `make all`
10. **ห้ามใส่ภาษาไทยใน HTTP header value** — Python จะ
    `UnicodeEncodeError: 'latin-1'` (เขียนเป็นเนื้อหาสอนไว้ในบทที่ 32.5 แล้ว)
11. **`pkill -f "lab/server.py"` ฆ่า shell ตัวเอง** เพราะ `-f` ไปแมตช์ command line
    ของ bash ที่รันคำสั่งนั้นเอง → ใช้ `fuser -k 8080/tcp`

## ธรรมเนียมของ repo

- **ทุกตัวเลขและทุก output ในหนังสือต้องมาจากการรันจริง** ห้ามแต่งขึ้น
  ถ้ารันไม่ได้ให้เขียนว่ารันไม่ได้ อย่าเดาผลลัพธ์
- เนื้อหาและคอมเมนต์เป็น**ภาษาไทย**
- `lab/` ใช้ **Python stdlib ล้วน** ไม่ต้อง `pip install`
  (ยกเว้น Playwright ในบท 17-18 และ pytest ซึ่งบอกวิธีติดตั้งไว้ในบท)
- endpoint ที่**จงใจให้มีช่องโหว่** (`/api/v1/orders/`, `/api/fetch`) ต้องมีคำเตือน
  กำกับทุกที่ที่พูดถึง และ SSRF ต้องเปิดด้วย `LAB_ENABLE_SSRF=1` เท่านั้น
- แก้บทแล้วต้องตรวจ 3 อย่าง: `make check` (mermaid) · `make web` (build ผ่าน) ·
  ลิงก์ภายในไม่เสีย
- ห้ามใส่ข้อมูลส่วนตัว/ภายในองค์กรลงในบท (IP ภายใน, ชื่อคน, hostname)
  ตัวอย่างที่ต้องมีชื่อผู้ใช้ให้ใช้ `student1`, `myuser`, `alice`

## โครงสร้าง

```
course/          53 บท (.md — อ่านบน GitHub ได้ตรง ๆ ด้วย)
  img/           SVG รองรับธีมสว่าง/มืด
lab/             server.py + สคริปต์ + เฉลย
  gpu/           lab ของส่วนที่ 8 (vram_calc, batching_demo, ldpreload_quota)
tools/           check-mermaid.py
_quarto.yml      ลำดับการอ่านจริง + 9 ส่วน
*.lua            strip-nav (ตัด nav ของ GitHub ออกจากหนังสือ), pdf-symbols
.github/         workflow เผยแพร่ขึ้น GitHub Pages
```

## เผยแพร่

GitHub Actions (`.github/workflows/publish.yml`) สร้าง HTML แล้ว deploy ขึ้น
GitHub Pages ทุกครั้งที่ push เข้า `main` — **ตรึงเวอร์ชัน Quarto ไว้ใน workflow**
ให้ตรงกับที่ใช้เขียน ไม่งั้นผลลัพธ์อาจต่างกันโดยไม่มีใครสังเกต
