# lab บทที่ 64 — เรียก C จาก Python
libfast.so: fast.c
	gcc -O2 -shared -fPIC -o libfast.so fast.c

demo: libfast.so
	@python3 call.py

clean:
	rm -f libfast.so
.PHONY: demo clean
