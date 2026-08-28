# บทที่ 30 · Git — อย่าทำงานโดยไม่มีตาข่ายรองรับ

> โปรเจกต์คอร์สนี้เขียนมา 30 บทโดยไม่มี git เลย
> ถ้าวันหนึ่งพิมพ์ `rm -rf` ผิดที่ คืองานหายทั้งหมด
>
> บทนี้สั้นและตรงไปตรงมา — เอาแค่ที่ใช้จริง

## 30.1 git แก้ปัญหาอะไร {#s30-1}

| ปัญหา | ถ้าไม่มี git | ถ้ามี git |
|-------|-------------|-----------|
| ลบไฟล์ผิด | หายถาวร | `git restore` กลับมาใน 1 วินาที |
| แก้แล้วพัง อยากย้อน | จำไม่ได้ว่าแก้อะไร | `git diff` เห็นทุกบรรทัดที่เปลี่ยน |
| อยากลองไอเดียใหม่ | ต้องคัดลอกทั้งโฟลเดอร์ | `git switch -c ทดลอง` |
| "เมื่อวานยังทำงานได้อยู่เลย" | เดา | `git log` + `git bisect` หาเจอว่า commit ไหนพัง |

**git ไม่ได้มีไว้ทำงานเป็นทีมอย่างเดียว** — คนทำงานคนเดียวได้ประโยชน์เต็ม ๆ จากข้อ 1, 2, 4

## 30.2 เริ่มใช้กับโปรเจกต์นี้เลย {#s30-2}

```bash
cd ~/Projects/anti-bot
git init
git add .
git commit -m "คอร์ส HTTP/curl 29 บท + lab server + รูปประกอบ"
```

แค่นี้งานทั้งหมดถูกบันทึกไว้แล้ว

> ⚠️ **ก่อน `git add .` ต้องมี `.gitignore` ก่อนเสมอ** ไม่งั้นจะเผลอ commit
> ของที่ไม่ควรเข้า — โดยเฉพาะ **cookie jar, token, `.env`** ซึ่งเป็น credential จริง
> ([บทที่ 20.4](20-shell-scripting-for-curl.md#s20-4)) โปรเจกต์นี้มี `.gitignore` เตรียมไว้ให้แล้ว

ตรวจว่าอะไรจะถูก commit ก่อนกดจริง:

```bash
git add .
git status              # ดูรายการ
git diff --cached       # ดูเนื้อหาที่จะเข้าไปจริง ๆ
```

## 30.3 หกคำสั่งที่ใช้ 95% ของเวลา {#s30-3}

```bash
git status              # ตอนนี้มีอะไรเปลี่ยนบ้าง  ← ใช้บ่อยที่สุด
git diff                # เปลี่ยนอะไรไปบ้าง (ยังไม่ add)
git add <file>          # เลือกว่าจะเอาอะไรเข้า commit นี้
git commit -m "ข้อความ"  # บันทึกจุดกลับ
git log --oneline       # ดูประวัติ
git restore <file>      # ทิ้งการแก้ กลับไปเป็นเวอร์ชันล่าสุดที่ commit
```

จำภาพนี้ไว้ก็พอ:

```mermaid
flowchart LR
    W["<b>Working directory</b><br/>ไฟล์ที่คุณกำลังแก้"]
    S["<b>Staging area</b><br/>ของที่เลือกไว้แล้ว<br/>ว่าจะเข้า commit นี้"]
    R["<b>Repository</b><br/>ประวัติถาวร"]

    W -->|"git add"| S
    S -->|"git commit"| R
    S -->|"git restore --staged"| W
    R -.->|"git restore / git checkout"| W
```

**staging area คือสิ่งที่ทำให้ git ต่างจากเครื่องมืออื่น** — มันให้คุณเลือกว่า
จะเอาการแก้ไข *บางส่วน* เข้า commit นี้ ไม่ต้องเอาทั้งหมด

## 30.4 commit ให้ดี {#s30-4}

**commit บ่อย ๆ ทีละเรื่อง** ดีกว่า commit ใหญ่ ๆ ทีเดียว

```bash
# ❌ commit เดียวปนกันหมด — ย้อนกลับทีหลังไม่ได้แยกส่วน
git commit -m "แก้เยอะ"

# ✅ แยกตามเรื่อง
git commit -m "เพิ่ม endpoint /api/logout"
git commit -m "แก้ BOLA ใน /api/v1/orders"
```

**ข้อความ commit ที่ดีตอบว่า "ทำไม" ไม่ใช่ "อะไร"**

```
❌ update server.py              ← ดู diff ก็รู้อยู่แล้ว
✅ แก้ BOLA: ตรวจ owner ก่อนคืน order

   เดิม /api/v1/orders/{id} ตรวจแค่ token ทำให้ผู้ใช้คนหนึ่ง
   ดู order ของคนอื่นได้ ตอนนี้เช็ค owner แล้วตอบ 404 (ไม่ใช่ 403)
   เพื่อไม่ให้ไล่เดา id ได้
```

บรรทัดแรกสั้น (< 60 ตัวอักษร) เว้นบรรทัด แล้วอธิบายเหตุผลข้างล่าง

## 30.5 กู้ของที่ทำพัง — 4 สถานการณ์ {#s30-5}

```bash
# 1. แก้ไฟล์แล้วอยากทิ้ง กลับเป็นเวอร์ชันล่าสุด
git restore course/01-http-basics.md

# 2. add ไปแล้วแต่ยังไม่ commit อยากเอาออกจาก staging
git restore --staged course/01-http-basics.md

# 3. commit ไปแล้วแต่ข้อความผิด (ยังไม่ push)
git commit --amend -m "ข้อความใหม่"

# 4. commit ไปแล้วอยากย้อน แต่เก็บประวัติไว้
git revert <hash>
```

**ดูว่าไฟล์เคยมีหน้าตายังไงเมื่อวาน:**

```bash
git log --oneline -- course/01-http-basics.md   # หา hash
git show <hash>:course/01-http-basics.md        # ดูเนื้อหาตอนนั้น
git diff <hash> -- course/01-http-basics.md     # เทียบกับตอนนี้
```

> **`git reset --hard` คือคำสั่งที่ลบงานจริง ๆ** — ใช้เมื่อแน่ใจเท่านั้น
> ของที่ยังไม่ commit จะหายถาวร ไม่มีทางกู้

## 30.6 Branch — ลองของโดยไม่กลัวพัง {#s30-6}

```bash
git switch -c ทดลอง-rate-limit     # สร้าง branch ใหม่แล้วย้ายไป
# ...แก้อะไรก็ได้...
git switch main                    # กลับมาที่เดิม ของเดิมอยู่ครบ

git merge ทดลอง-rate-limit         # ถ้าชอบ เอาเข้า main
git branch -D ทดลอง-rate-limit     # ถ้าไม่ชอบ ลบทิ้ง
```

**นี่คือเหตุผลหลักที่คนทำงานคนเดียวควรใช้ git** — ลองไอเดียเสี่ยง ๆ ได้โดยไม่ต้อง
คัดลอกโฟลเดอร์ แล้วถ้าไม่เวิร์กก็ทิ้งได้สะอาด

## 30.7 ⚠️ ความลับที่หลุดขึ้น git {#s30-7}

นี่คือจุดที่คนทำ API พลาดกันบ่อยที่สุด และเชื่อมกับ[บทที่ 25.8](25-input-validation-and-injection.md#s25-8) โดยตรง

```bash
# สแกนก่อน commit
git diff --cached | grep -iE 'password|secret|token|api[_-]?key|BEGIN.*PRIVATE'
```

**ถ้า secret หลุดขึ้น git ไปแล้ว:**

1. **หมุน secret ทันที** — นี่คือขั้นแรกเสมอ
2. อย่าคิดว่าแค่ลบ commit แล้วจบ — ถ้า push ไปแล้ว มันถูก clone/cache/index ไปแล้ว
3. ล้างประวัติด้วย [`git-filter-repo`](https://github.com/newren/git-filter-repo) (ถ้าจำเป็น)

**การลบไฟล์ใน commit ใหม่ไม่ได้ลบมันออกจากประวัติ** — `git log -p` ยังเห็นอยู่

เครื่องมือช่วย: `gitleaks detect`, `trufflehog`, และเปิด secret scanning ถ้าใช้ GitHub

## 30.8 ตั้งค่าครั้งเดียวจบ {#s30-8}

```bash
git config --global user.name "ชื่อคุณ"
git config --global user.email "อีเมลคุณ"
git config --global init.defaultBranch main
git config --global pull.rebase true          # ประวัติสะอาดกว่า
git config --global core.editor "code --wait" # ใช้ VS Code เขียน commit message
```

**alias ที่ช่วยได้จริง:**

```bash
git config --global alias.s  "status -sb"
git config --global alias.l  "log --oneline --graph --decorate -20"
git config --global alias.d  "diff"
git config --global alias.last "log -1 --stat"
```

## 30.9 ทำงานกับ remote (GitHub) {#s30-9}

```bash
git remote add origin git@github.com:you/anti-bot.git
git push -u origin main        # ครั้งแรก
git push                       # ครั้งต่อไป
git pull                       # ดึงของใหม่มา
```

**ใช้ SSH key ไม่ใช่ password** — GitHub เลิกรองรับ password แล้ว

```bash
ssh-keygen -t ed25519 -C "อีเมลคุณ"
cat ~/.ssh/id_ed25519.pub      # เอาไปใส่ใน GitHub Settings → SSH keys
ssh -T git@github.com          # ทดสอบ
```

> คอร์สนี้เก็บบทเรียนเป็น `.md` โดยตั้งใจ ([บทที่ 30.10](#s30-10) ของแผน) เพราะ
> **GitHub render markdown และ mermaid ให้อ่านได้ทันที** โดยไม่ต้อง build อะไร

## 30.10 หาว่าอะไรทำให้พัง — `git bisect` {#s30-10}

เมื่อ "เมื่อวานยังทำงานได้" แต่วันนี้พัง และมี commit คั่นกลาง 40 อัน

```bash
git bisect start
git bisect bad                 # ตอนนี้พัง
git bisect good <hash-เมื่อวาน> # ตอนนั้นดี
# git จะพาไปที่ commit ตรงกลาง ให้คุณทดสอบแล้วบอกว่า good หรือ bad
git bisect good   # หรือ  git bisect bad
# ...ทำซ้ำ ~6 ครั้ง สำหรับ 40 commit...
git bisect reset
```

**binary search บนประวัติ** — 40 commit หาเจอใน 6 ครั้ง แทนที่จะไล่ทีละอัน
ถ้ามีเทสต์อัตโนมัติ ([บทที่ 32](32-testing-with-pytest.md)) ใช้ `git bisect run pytest` ให้มันหาเองได้เลย

## แบบฝึกหัด

1. `git init` โปรเจกต์นี้ แล้ว commit แรกให้สำเร็จ — ตรวจด้วย `git status`
   ว่าไม่มี `_book/`, `.quarto/` หรือไฟล์ cookie หลุดเข้าไป
2. แก้ไฟล์บทเรียนสักบท แล้วดู `git diff` ก่อน commit
3. ทำพังโดยตั้งใจ: ลบเนื้อหาครึ่งไฟล์แล้วบันทึก จากนั้นกู้ด้วย `git restore`
4. สร้าง branch ทดลอง แก้อะไรสักอย่าง แล้วกลับมา `main` ดูว่าของเดิมอยู่ครบ
5. ตั้ง alias 4 ตัวใน[ข้อ 30.8](#s30-8) แล้วลองใช้ `git s` กับ `git l`
6. สร้างไฟล์ที่มีคำว่า `API_KEY=sk_live_12345` แล้วลอง `git add` — คำสั่ง grep
   ใน[ข้อ 30.7](#s30-7) จับได้ไหม
7. ทำ commit 5 อัน แล้วใช้ `git log -p` ดูว่าเห็นเนื้อหาที่เคยลบไปแล้วหรือเปล่า

***
[⬅ Push, Real-time, Upload และ Offline](29-realtime-push-and-offline.md) · [สารบัญ](../README.md) · [เขียน bash ให้ปลอดภัยและไม่พังเงียบ  ➡](20-shell-scripting-for-curl.md)
