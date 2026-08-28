# lab บทที่ 67 — profiling
profile:
	@echo "=== cProfile: หาว่าฟังก์ชันไหนกินเวลา ==="
	@python3 -m cProfile -s tottime slow.py 2>&1 | head -12

compare:
	@python3 compare.py

.PHONY: profile compare
