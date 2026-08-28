# คำสั่งลัดสำหรับคอร์สนี้
#
#   make          — ดูรายการคำสั่งทั้งหมด
#   make web      — สร้างเว็บแล้วเปิดดู (ใช้บ่อยที่สุด)
#   make lab      — เปิด lab server
#   make check    — รันเฉลยทุกตัวเพื่อยืนยันว่า lab ยังทำงาน

.DEFAULT_GOAL := help
.PHONY: help web preview book all lab lab-ssrf check clean

help:
	@echo ""
	@echo "  อ่านหนังสือ"
	@echo "    make preview    เปิดเว็บพร้อม auto-reload (แนะนำตอนอ่าน/แก้)"
	@echo "    make web        สร้างเว็บอย่างเดียว → _book/index.html"
	@echo "    make book       สร้าง PDF + EPUB"
	@echo "    make all        สร้างครบทั้งสามแบบ"
	@echo ""
	@echo "  ฝึกมือ"
	@echo "    make lab        เปิด lab server ที่ http://127.0.0.1:8080"
	@echo "    make lab-ssrf   เปิด lab พร้อม endpoint SSRF (แบบฝึกหัดบทที่ 25)"
	@echo "    make check      รันเฉลยทุกตัวเพื่อยืนยันว่า lab ยังทำงานปกติ"
	@echo ""
	@echo "    make clean      ลบผลลัพธ์ที่สร้างไว้"
	@echo ""

# ── หนังสือ ───────────────────────────────────────────────────
preview:
	quarto preview

web:
	quarto render --to html
	@echo ""
	@echo "เปิดไฟล์นี้ในเบราว์เซอร์:"
	@echo "  file://$(CURDIR)/_book/index.html"

book:
	quarto render --to pdf
	quarto render --to epub

# render ทีเดียวให้ครบ - ถ้าสั่งทีละ format Quarto จะล้างของเดิมทิ้ง
all:
	quarto render
	@ls -lh _book/*.pdf _book/*.epub 2>/dev/null || true

# ── lab ──────────────────────────────────────────────────────
lab:
	python3 lab/server.py

lab-ssrf:
	LAB_ENABLE_SSRF=1 python3 lab/server.py

check:
	@echo "เปิด lab server ชั่วคราว..."
	@fuser -k 8080/tcp 2>/dev/null || true
	@sleep 1
	@python3 lab/server.py > /dev/null 2>&1 & sleep 2; \
	 fail=0; \
	 for s in login-flow auth-flow pow-flow; do \
	   if bash lab/solutions/$$s.sh > /dev/null 2>&1; \
	     then echo "  ok   $$s.sh"; \
	     else echo "  FAIL $$s.sh"; fail=1; fi; \
	 done; \
	 python3 lab/solutions/playwright_cookies.py --demo > /dev/null 2>&1 \
	   && echo "  ok   playwright_cookies.py --demo" || echo "  FAIL playwright_cookies.py"; \
	 python3 lab/db_demo.py > /dev/null 2>&1 \
	   && echo "  ok   db_demo.py" || echo "  FAIL db_demo.py"; \
	 fuser -k 8080/tcp 2>/dev/null || true; \
	 exit $$fail

clean:
	rm -rf _book .quarto
	rm -f index.log index.tex
	@echo "ลบผลลัพธ์แล้ว"
