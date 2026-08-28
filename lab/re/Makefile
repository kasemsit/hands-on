# lab บทที่ 63 — แกะและแก้ binary
crackme: crackme.c
	gcc -O0 -no-pie -o crackme crackme.c

demo: crackme
	@echo "=== รันปกติ ==="
	@./crackme s3cr3t; echo "  exit=$$?"
	@./crackme wrong;  echo "  exit=$$?"
	@echo
	@echo "=== หา sete แล้วพลิกเป็น setne (แก้ 1 ไบต์) ==="
	@python3 patch.py
	@chmod +x crackme_patched
	@echo "=== binary ที่แก้แล้ว — ตรรกะกลับด้าน ==="
	@./crackme_patched wrong; echo "  exit=$$?  (รหัสผิดกลับผ่าน)"

clean:
	rm -f crackme crackme_patched
.PHONY: demo clean
