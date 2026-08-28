# lab 67 — profiling

หา "จุดร้อน" ในโค้ด Python ด้วยเครื่องมือที่มากับ stdlib

```bash
make profile     # cProfile ชี้ว่าฟังก์ชันไหนกินเวลา
make compare     # วัดผลก่อน/หลังแก้ — fib memoize เร็วขึ้นหลักหมื่นเท่า
```

## ไฟล์

| ไฟล์ | คืออะไร |
|------|---------|
| `slow.py` | โปรแกรมช้า — `fib` recursion ซ้ำซ้อน |
| `compare.py` | วัดก่อน/หลัง memoize |
