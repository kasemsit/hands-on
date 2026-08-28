# lab บทที่ 49.8 — HAMi ดัก CUDA API ด้วย LD_PRELOAD ได้อย่างไร
# ตัวอย่างนี้ดัก malloc แทน cuMemAlloc จึงรันได้แม้ไม่มี GPU

CFLAGS = -Wall -O2

all: quota.so app

quota.so: quota.c
	$(CC) $(CFLAGS) -shared -fPIC -o $@ $< -ldl

app: app.c
	$(CC) $(CFLAGS) -o $@ $<

demo: all
	@echo "=== รันปกติ ==="
	@./app
	@echo
	@echo "=== รันโดยมี shim ดักไว้ ==="
	@LD_PRELOAD=./quota.so ./app

clean:
	rm -f quota.so app

.PHONY: all demo clean
