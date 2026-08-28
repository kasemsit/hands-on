# บทที่ 35 · Linux internals ที่คนทำ API ต้องรู้

> ตลอดคอร์สนี้คุณเจอเรื่องระดับ OS มาแล้วโดยไม่รู้ตัว — `fuser -k 8080/tcp`,
> `CLOSE-WAIT` เยอะแปลว่ารั่ว, `pkill -f` ที่ฆ่า shell ตัวเอง
>
> บทนี้อธิบายว่าทำไมสิ่งเหล่านั้นเป็นแบบนั้น

## 35.1 ทุกอย่างคือไฟล์ (หรือทำตัวเหมือนไฟล์)

นี่คือแนวคิดหลักของ Unix ที่อธิบายเรื่องอื่นเกือบทั้งหมด

```bash
PID=$(pgrep -f 'lab/server.py' | head -1)
ls -l /proc/$PID/fd
```

```
lr-x------ 0 -> /dev/null
l-wx------ 1 -> /dev/null
lrwx------ 2 -> /dev/null
lrwx------ 3 -> socket:[4475429]
```

**`3 -> socket:[...]` คือ TCP socket ที่ listen อยู่ที่ port 8080** — ระบบปฏิบัติการ
มองมันเป็น "ไฟล์" หมายเลข 3 ที่โปรแกรมอ่าน/เขียนได้เหมือนไฟล์ธรรมดา

| fd | ชื่อ | ปกติคือ |
|----|------|---------|
| 0 | stdin | คีย์บอร์ด |
| 1 | stdout | จอ |
| 2 | stderr | จอ (แยกจาก stdout) |
| 3+ | อะไรก็ได้ | ไฟล์, socket, pipe |

**นี่คือเหตุผลที่ `2>/dev/null` ทำงาน** — คุณกำลังบอกว่า "เอา fd 2 ไปชี้ที่ถังขยะ"
และเป็นเหตุผลที่ `nc -l ... > raw.bin` แยกข้อมูลออกจากข้อความสถานะได้
(ภาคผนวก A.4) เพราะสองอย่างนั้นออกคนละ fd

## 35.2 File descriptor หมด = server ตาย

```bash
grep 'open files' /proc/$PID/limits
```

```
Max open files            1048576              1048576              files
```

ทุก connection ที่เข้ามากิน 1 fd **ถ้าโค้ดลืมปิด fd จะสะสมจนหมด** แล้ว
server จะรับ connection ใหม่ไม่ได้เลย

```python
# ❌ fd รั่ว
f = open("data.txt")
data = f.read()          # ถ้าพังตรงนี้ ไฟล์ไม่เคยถูกปิด

# ✅ ปิดให้เสมอแม้เกิด exception
with open("data.txt") as f:
    data = f.read()
```

**อาการเวลา fd หมด:**

```
OSError: [Errno 24] Too many open files
```

**วิธีตรวจ** (โยงกับ `CLOSE-WAIT` ในบทที่ 31.5):

```bash
ls /proc/$PID/fd | wc -l           # ใช้ไปเท่าไรแล้ว
lsof -p $PID | wc -l               # แบบละเอียด
ss -tan state close-wait | wc -l   # connection ที่ลืมปิด
```

**ถ้าตัวเลขนี้โตขึ้นเรื่อย ๆ ตามเวลา = รั่วแน่นอน** ไม่ใช่โหลดเยอะ

## 35.3 Process — เกิด ตาย และผีดิบ

```mermaid
flowchart LR
    P["<b>parent</b>"] -->|"fork()"| C["<b>child</b><br/>สำเนาของ parent"]
    C -->|"exec()"| N["<b>โปรแกรมใหม่</b><br/>ทับตัวเองด้วยโปรแกรมอื่น"]
    N -->|"exit()"| Z["<b>zombie</b><br/>ตายแล้วแต่ยังอยู่ในตาราง"]
    Z -->|"parent เรียก wait()"| G["หายไปจริง"]

    style Z fill:#fff8c5,stroke:#d4a72c
```

**`fork` + `exec` คือวิธีที่ทุกโปรแกรมบน Linux ถูกเรียกใช้** — shell ของคุณ
`fork` ตัวเองแล้ว `exec` เป็น `curl`

| สถานะ | แปลว่า | เห็นใน `ps` เป็น |
|-------|--------|------------------|
| Running / Runnable | กำลังทำงานหรือรอ CPU | `R` |
| Sleeping | รอ I/O (ปกติมาก) | `S` |
| **Zombie** | ตายแล้วแต่ parent ยังไม่เก็บศพ | `Z` |
| **Uninterruptible sleep** | ติดใน I/O ที่ฆ่าไม่ได้ | `D` ⚠️ |

**Zombie เยอะ = parent ลืม `wait()`** ไม่กิน CPU หรือ RAM แต่กินช่องในตาราง process
เจอบ่อยในโค้ดที่ `subprocess.Popen()` แล้วไม่เคย `.wait()`

```python
proc = subprocess.Popen([...])
# ... ทำอะไรสักอย่าง ...
proc.wait()          # ← ต้องมี ไม่งั้นได้ zombie
```

**สถานะ `D` คือตัวที่น่ากลัวกว่า** — `kill -9` ก็ไม่ตาย เพราะมันติดอยู่ใน
syscall ที่ขัดจังหวะไม่ได้ (เช่นรอ disk หรือ NFS ที่ค้าง) ต้องแก้ที่ต้นเหตุ

## 35.4 Signal — วิธีบอกให้ process ทำอะไร

| Signal | เลข | ความหมาย | จับได้ไหม |
|--------|-----|----------|-----------|
| `SIGTERM` | 15 | "ขอให้จบงานแล้วปิด" | ✅ **ค่าเริ่มต้นของ `kill`** |
| `SIGINT` | 2 | Ctrl-C | ✅ |
| `SIGKILL` | 9 | ฆ่าทันที | ❌ **จับไม่ได้ เก็บกวาดไม่ได้** |
| `SIGHUP` | 1 | terminal ปิด / "โหลด config ใหม่" | ✅ |
| `SIGPIPE` | 13 | เขียนลง pipe ที่อีกฝั่งปิดแล้ว | ✅ |

**นี่คือหัวใจของ graceful shutdown ในบทที่ 28.8**

```python
import signal

def handle_sigterm(signum, frame):
    global shutting_down
    shutting_down = True       # /health/ready เริ่มตอบ 503

signal.signal(signal.SIGTERM, handle_sigterm)
```

> ⚠️ **อย่าใช้ `kill -9` เป็นนิสัย** — โปรแกรมไม่มีโอกาสปิด connection,
> flush log, หรือ commit transaction ค้าง ใช้ `kill` (SIGTERM) ก่อนเสมอ
> แล้วรอสัก 10 วินาที ค่อยใช้ `-9` ถ้าจำเป็นจริง

**`SIGPIPE` อธิบายเรื่องที่เจอในภาคผนวก A** — เวลา `curl` ตัดสายก่อนที่ server
จะเขียนเสร็จ server จะได้ SIGPIPE ซึ่งใน `lab/server.py` เราจับไว้ด้วย
`except BrokenPipeError`

## 35.5 หา process ให้ถูกตัว

จำเรื่องที่ผมพลาดตอนต้นคอร์สได้ไหม — `pkill -f "lab/server.py"` **ฆ่า shell ตัวเอง**
เพราะ `-f` เทียบกับ command line ทั้งบรรทัด และ shell ที่รันคำสั่งนั้น
ก็มีข้อความ `lab/server.py` อยู่ในบรรทัดของตัวเองด้วย

```bash
# ❌ เสี่ยงฆ่าตัวเอง
pkill -f "lab/server.py"

# ✅ อ้างอิงจากพอร์ต — ไม่เกี่ยวกับชื่อคำสั่ง
fuser -k 8080/tcp

# ✅ หาก่อนแล้วค่อยฆ่า
ss -tlnp | grep 8080
lsof -ti :8080 | xargs -r kill
```

| เครื่องมือ | ใช้ตอน |
|-----------|--------|
| `ps aux \| grep X` | ดูคร่าว ๆ (แต่จะเจอ grep ตัวเองด้วย) |
| `pgrep -a X` | หา PID พร้อม command line |
| `lsof -i :8080` | ใครถือพอร์ตนี้ |
| `fuser -k 8080/tcp` | **ฆ่าคนที่ถือพอร์ต — ปลอดภัยที่สุด** |
| `ss -tlnp` | ดู listening socket ทั้งหมด |

## 35.6 `/proc` — หน้าต่างเข้าไปดูในเคอร์เนล

`/proc` ไม่ใช่ไฟล์จริงบนดิสก์ — เป็นหน้าต่างที่เคอร์เนลเปิดให้ดูสถานะระบบ

```bash
cat /proc/$PID/cmdline | tr '\0' ' '   # คำสั่งเต็มที่ใช้เรียก
cat /proc/$PID/status                  # สถานะ, RAM, จำนวน thread
cat /proc/$PID/environ | tr '\0' '\n'  # ⚠️ environment variable
ls /proc/$PID/task | wc -l             # จำนวน thread
cat /proc/$PID/io                      # อ่าน/เขียนไปเท่าไร
```

> ⚠️ **`/proc/PID/environ` คือเหตุผลที่บทที่ 20.4 บอกว่า environment variable
> ยังไม่ใช่ที่ปลอดภัยที่สุดสำหรับ secret** — เจ้าของ process (และ root)
> อ่านได้ ถ้า token อยู่ใน env มันอยู่ตรงนี้

```bash
cat /proc/loadavg      # โหลดเฉลี่ย 1, 5, 15 นาที
cat /proc/meminfo      # หน่วยความจำ
```

**อ่าน load average ให้ถูก** — ตัวเลข `2.5` บนเครื่อง 4 core แปลว่าใช้ไป
ประมาณ 62% ไม่ใช่ 250% **ต้องเทียบกับจำนวน core เสมอ** (`nproc`)

## 35.7 `strace` — เห็นทุก syscall ที่โปรแกรมเรียก

`strace` คือ `tcpdump` ของ syscall — เห็นทุกคำสั่งที่โปรแกรมขอจากเคอร์เนล

```bash
strace -f -e trace=network -p $PID       # ดู process ที่รันอยู่
strace -f -o out.txt curl http://...     # รันใหม่แล้วบันทึก
strace -c curl http://...                # สรุปว่าเรียก syscall ไหนกี่ครั้ง
strace -e trace=openat ls                # เฉพาะการเปิดไฟล์
```

**ต้องมีสิทธิ์ ptrace** — บนหลายระบบถูกจำกัดไว้:

```bash
cat /proc/sys/kernel/yama/ptrace_scope   # 0 = ทำได้ทุก process ของเรา, 1 = เฉพาะลูก
sudo strace -p $PID                      # หรือใช้ sudo
```

**ใช้แก้ปัญหาอะไรได้บ้าง:**

| ปัญหา | ดูอะไร |
|-------|--------|
| "หาไฟล์ config ไม่เจอ" | `strace -e trace=openat` เห็นว่ามันไปหาที่ไหนบ้าง |
| "โปรแกรมค้าง" | `strace -p $PID` เห็นว่าค้างที่ syscall ไหน |
| "ช้าโดยไม่รู้สาเหตุ" | `strace -c` เห็นว่า syscall ไหนถูกเรียกเป็นแสนครั้ง |
| "permission denied ที่ไหน" | เห็น `EACCES` ตรง ๆ ว่าไฟล์ไหน |

```
openat(AT_FDCWD, "/etc/myapp.conf", O_RDONLY) = -1 ENOENT (No such file or directory)
```

บรรทัดเดียวนี้ตอบคำถามได้ทันทีว่าโปรแกรมหา config ที่ไหน

## 35.8 Environment variable และ process

```bash
env | sort                 # ของ shell ปัจจุบัน
cat /proc/$PID/environ     # ของ process อื่น
```

**environment สืบทอดจาก parent ไปลูก** — นี่คือเหตุผลที่:

```bash
export API_TOKEN=xxx
python3 app.py             # app.py เห็น API_TOKEN

API_TOKEN=xxx python3 app.py   # ตั้งเฉพาะคำสั่งนี้ ไม่ค้างใน shell
```

และเป็นเหตุผลที่ **การ `export` ใน shell script ไม่มีผลกับ shell แม่**
เพราะ script รันใน process ลูก

## 35.9 systemd — วิธีที่ service จริงถูกรัน

lab server ของเรารันด้วย `python3 lab/server.py &` ซึ่งตายเมื่อปิด terminal
ของจริงต้องใช้ service manager

```ini
# /etc/systemd/system/myapi.service
[Unit]
Description=My API
After=network.target

[Service]
Type=simple
User=myapi                      # ← ห้ามรันเป็น root (บทที่ 36)
WorkingDirectory=/srv/myapi
EnvironmentFile=/etc/myapi/env  # secret อยู่ในไฟล์ที่ chmod 600
ExecStart=/srv/myapi/.venv/bin/python -m myapi
Restart=on-failure
RestartSec=5

# จำกัดสิทธิ์ (บทที่ 36)
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now myapi
systemctl status myapi
journalctl -u myapi -f          # ดู log แบบ tail -f
journalctl -u myapi --since "1 hour ago" -p err
```

**`systemctl reload` vs `restart`** — `reload` ส่ง SIGHUP ให้โหลด config ใหม่
โดยไม่ตัด connection ส่วน `restart` คือหยุดแล้วเริ่มใหม่
(ถ้าทำ graceful shutdown ไว้ตามบทที่ 28.8 การ restart ก็ไม่ตัด request กลางคัน)

## 35.10 เมื่อ RAM หมด — OOM killer

Linux ยอมให้จองหน่วยความจำเกินที่มีจริง (overcommit) พอใช้จริงจนหมด
เคอร์เนลจะ**เลือกฆ่า process สักตัว**

```bash
dmesg -T | grep -i 'killed process'
journalctl -k | grep -i oom
```

```
Out of memory: Killed process 12345 (python3) total-vm:8000000kB
```

**อาการที่หลอกตา:** แอปหายไปเฉย ๆ ไม่มี error ใน log ของแอปเอง เพราะมันถูก
SIGKILL ซึ่ง**จับไม่ได้** (ข้อ 35.4) — ต้องไปดูที่ log ของเคอร์เนล

**ป้องกัน:** ตั้ง memory limit ให้ service, ตรวจ memory leak, และ**ตั้ง alert
ที่ memory ก่อนถึงขีด** (บทที่ 28.6)

## 35.11 เชื่อมกับสิ่งที่เจอมาแล้วในคอร์ส

| เคยเจอที่ไหน | คำอธิบายระดับ OS |
|--------------|------------------|
| `fuser -k 8080/tcp` (บท 21) | หา process ที่ถือ fd ของ socket นั้น |
| `CLOSE-WAIT` เยอะ (บท 31.5) | fd รั่ว — โค้ดลืมปิด |
| graceful shutdown (บท 28.8) | จับ SIGTERM |
| `2>/dev/null` | เปลี่ยนปลายทางของ fd 2 |
| `nc -l > raw.bin` (ภาคผนวก A) | stdout กับ stderr เป็นคนละ fd |
| pool ใหญ่เกิน (บท 27.4) | connection แต่ละเส้นกิน fd |
| `export TOKEN=` (บท 20.4) | อยู่ใน `/proc/PID/environ` |

## แบบฝึกหัด

1. หา PID ของ lab server แล้วดู `/proc/$PID/fd` — มี fd อะไรบ้าง socket อยู่ตัวไหน
2. ยิง `curl` ใส่ lab server หลาย ๆ ครั้งพร้อมกัน แล้วนับ fd ระหว่างนั้น
   ```bash
   for i in $(seq 20); do curl -s http://127.0.0.1:8080/slow & done
   ls /proc/$PID/fd | wc -l
   ```
3. เขียนสคริปต์ Python ที่เปิดไฟล์ในลูปโดยไม่ปิด แล้วดูว่าถึง `Errno 24` เมื่อไร
4. ใช้ `strace -c curl http://127.0.0.1:8080/api/books` ดูว่า syscall ไหนถูกเรียกมากสุด
5. ใช้ `strace -e trace=openat python3 -c "import json"` — Python หาไฟล์ที่ไหนบ้าง
6. สร้าง zombie: `subprocess.Popen(["true"])` โดยไม่ `.wait()` แล้วดู `ps aux | grep Z`
7. ส่ง `kill -TERM` กับ `kill -9` ให้ lab server เทียบกัน — ต่างกันอย่างไรใน log
8. เขียน systemd unit ให้ lab server แล้วทดสอบ `systemctl restart` ระหว่างที่ยิง load ค้างไว้

***
[⬅ ชั้นใต้ HTTP](31-tcpip-and-tcpdump.md) · [สารบัญ](../README.md) · [สิทธิ์และการแยกส่วน ➡](36-permissions-and-isolation.md)
