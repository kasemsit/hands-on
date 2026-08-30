# Hands-on Systems

> จาก curl ถึง GPU — คู่มือลงมือทำที่ทุกตัวเลขมาจากการรันจริง

📖 **อ่านออนไลน์: <https://kasemsit.github.io/hands-on/>**

เอกสารชุดนี้สอนตั้งแต่ศูนย์ — จาก "HTTP คืออะไร" ถึงการออกแบบ API ความปลอดภัยของระบบ
และ GPU/AI infrastructure
ทุกบทมี **แบบฝึกหัดที่ยิงใส่ lab server บนเครื่องคุณเอง** ไม่ต้องไปทดลองกับเว็บคนอื่น

**ทุกตัวเลขและ output ในเล่มนี้มาจากการรันจริง** ไม่มีตัวอย่างที่แต่งขึ้น

## อ่านแบบไหนก็ได้

| แบบ | คำสั่ง | เหมาะกับ |
|-----|--------|----------|
| **เว็บ** (แนะนำ) | [อ่านออนไลน์](https://kasemsit.github.io/hands-on/) หรือ `make preview` | สารบัญข้างซ้าย · ค้นหาได้ · **ลิงก์ข้ามบทกดได้** |
| **ไฟล์ .md** | เปิดใน IDE | แก้เนื้อหา · ลิงก์ข้ามบทต้องอ่านบนเว็บถึงจะกดได้ |
| **PDF / EPUB** | `make book` | อ่านออฟไลน์ บนแท็บเล็ต |

สร้างเว็บครั้งเดียวแล้วเปิดไฟล์:

```bash
make web
# → เปิด _book/index.html ในเบราว์เซอร์
```

ต้องมี [Quarto](https://quarto.org/docs/get-started/) ติดตั้งไว้ก่อน
ถ้าไม่อยากลง อ่านไฟล์ `.md` ใน [course/](course/) ตรง ๆ ก็ได้เนื้อหาเหมือนกันทุกอย่าง

## เริ่มยังไง

เปิด terminal สองหน้าต่าง

หน้าต่างที่ 1 — เปิด lab server ทิ้งไว้:

```bash
python3 lab/server.py
```

หน้าต่างที่ 2 — ลองยิงดู:

```bash
curl -i http://127.0.0.1:8080/
```

ถ้าเห็น HTML ตอบกลับมา แปลว่าพร้อมเรียนแล้ว เปิด <http://127.0.0.1:8080> ในเบราว์เซอร์
เพื่อดูรายการ endpoint ทั้งหมดได้ด้วย

## แผนที่คอร์ส

### ส่วนที่ 1 · พื้นฐาน HTTP และ curl

| บท | เรื่อง |
|----|--------|
| [บทที่ 1](course/01-http-basics.md) | HTTP พื้นฐาน |
| [บทที่ 2](course/02-curl-basics.md) | curl พื้นฐาน |
| [บทที่ 3](course/03-html-forms.md) | HTML form → curl |
| [บทที่ 4](course/04-cookies-sessions.md) | Cookie และ Session |
| [บทที่ 5](course/05-redirects-and-headers.md) | Redirect และ Header |
| [บทที่ 6](course/06-encoding-and-charset.md) | Encoding, ภาษาไทย และ base64 |
| [บทที่ 7](course/07-tls-https.md) | TLS และ HTTPS |

### ส่วนที่ 2 · API และ Authentication

| บท | เรื่อง |
|----|--------|
| [บทที่ 8](course/08-json-api-and-jq.md) | JSON API และ jq |
| [บทที่ 9](course/09-authentication.md) | Authentication — Basic, API key, Bearer |
| [บทที่ 10](course/10-jwt-deep-dive.md) | JWT เจาะลึก |
| [บทที่ 53](course/53-oauth-and-oidc.md) | OAuth 2.0 และ OpenID Connect |
| [บทที่ 54](course/54-passkeys-and-webauthn.md) | Passkey และ WebAuthn |
| [บทที่ 11](course/11-mobile-api-auth-design.md) | ออกแบบ Authentication ให้ Mobile API |
| [บทที่ 12](course/12-api-design-practices.md) | API Design ที่ดี |
| [บทที่ 13](course/13-webhooks-and-hmac.md) | Webhook และ HMAC Signature |

### ส่วนที่ 3 · ออกแบบระบบให้อยู่รอด

| บท | เรื่อง |
|----|--------|
| [บทที่ 24](course/24-authorization-and-bola.md) | Authorization และ BOLA/IDOR |
| [บทที่ 25](course/25-input-validation-and-injection.md) | Input validation, Injection, SSRF และการอัปโหลดไฟล์ |
| [บทที่ 26](course/26-proxy-caching-cdn.md) | Reverse proxy, X-Forwarded-For, Caching และ CDN |
| [บทที่ 27](course/27-database-and-performance.md) | Database และ Performance ของ API |
| [บทที่ 71](course/71-transactions-and-isolation.md) | Transaction และ Isolation |
| [บทที่ 28](course/28-observability-and-deployment.md) | Observability และ Deployment |
| [บทที่ 68](course/68-observability-deep.md) | Observability เจาะลึก — trace |
| [บทที่ 29](course/29-realtime-push-and-offline.md) | Push, Real-time, Upload และ Offline |
| [บทที่ 69](course/69-websocket-sse-deep.md) | Real-time เจาะลึก — SSE, WebSocket |
| [บทที่ 56](course/56-background-jobs-and-queues.md) | งานเบื้องหลังและคิวงาน |
| [บทที่ 57](course/57-scaling-out.md) | ขยายระบบออกหลายเครื่อง |

### ส่วนที่ 4 · เครื่องมือของคนทำงาน

| บท | เรื่อง |
|----|--------|
| [บทที่ 30](course/30-git.md) | Git — อย่าทำงานโดยไม่มีตาข่ายรองรับ |
| [บทที่ 20](course/20-shell-scripting-for-curl.md) | เขียน bash ให้ปลอดภัยและไม่พังเงียบ ๆ |
| [บทที่ 32](course/32-testing-with-pytest.md) | เขียนเทสต์ให้ API |
| [บทที่ 55](course/55-ci-cd.md) | CI/CD — ท่อที่เชื่อมทุกอย่างเข้าด้วยกัน |
| [บทที่ 67](course/67-profiling.md) | Profiling — หาจุดที่ช้าจริง |
| [บทที่ 33](course/33-concurrency-and-async.md) | Concurrency และ async |
| [บทที่ 21](course/21-debugging-and-pitfalls.md) | Debug และกับดักที่เจอบ่อย |
| [ภาคผนวก A](course/A1-netcat.md) | netcat (`nc`) — เครื่องมือดูของจริง |

### ส่วนที่ 5 · เข้าใจฝั่งตรงข้าม — Automation และ Anti-bot

| บท | เรื่อง |
|----|--------|
| [บทที่ 14](course/14-devtools-to-curl.md) | DevTools → curl |
| [บทที่ 15](course/15-captcha-and-antibot.md) | CAPTCHA และสถาปัตยกรรม Anti-bot |
| [บทที่ 16](course/16-altcha-pow.md) | ALTCHA และ Proof of Work |
| [บทที่ 17](course/17-playwright-basics.md) | Playwright เบื้องต้น |
| [บทที่ 18](course/18-playwright-cookies-to-curl.md) | จาก Playwright สู่ curl — เทคนิคลูกผสม |
| [บทที่ 19](course/19-mitmproxy-mobile-traffic.md) | ดัก traffic ของ mobile app |

### ส่วนที่ 6 · ชั้นใต้ HTTP และระบบปฏิบัติการ

| บท | เรื่อง |
|----|--------|
| [บทที่ 31](course/31-tcpip-and-tcpdump.md) | ชั้นใต้ HTTP — TCP/IP และ tcpdump |
| [บทที่ 35](course/35-linux-internals.md) | Linux internals ที่คนทำ API ต้องรู้ |
| [บทที่ 36](course/36-permissions-and-isolation.md) | สิทธิ์และการแยกส่วน |
| [บทที่ 37](course/37-memory-and-classic-exploits.md) | หน่วยความจำและช่องโหว่คลาสสิก |
| [บทที่ 63](course/63-reverse-engineering.md) | Reverse engineering เบื้องต้น |
| [บทที่ 64](course/64-ffi-and-bindings.md) | เรียกข้ามภาษา — FFI และ binding |
| [บทที่ 65](course/65-linking-and-loading.md) | Linking และ loading |
| [บทที่ 38](course/38-crypto-in-practice.md) | Cryptography ภาคปฏิบัติ |

### ส่วนที่ 7 · Malware และการตั้งรับ

| บท | เรื่อง |
|----|--------|
| [บทที่ 39](course/39-how-malware-works.md) | มัลแวร์ทำงานอย่างไร |
| [บทที่ 40](course/40-malware-analysis-basics.md) | การวิเคราะห์มัลแวร์เบื้องต้น |
| [บทที่ 41](course/41-detection-and-response.md) | การตรวจจับและตอบสนอง |
| [บทที่ 42](course/42-supply-chain-security.md) | Supply chain security |
| [บทที่ 58](course/58-cloud-security.md) | ความปลอดภัยบนคลาวด์ |
| [บทที่ 59](course/59-network-defense.md) | ออกแบบเครือข่ายให้ป้องกันได้ |

### ส่วนที่ 8 · GPU และ AI Infrastructure

| บท | เรื่อง |
|----|--------|
| [บทที่ 46](course/46-gpu-101.md) | GPU 101 สำหรับคนที่มาจาก data science |
| [บทที่ 47](course/47-gpu-memory-and-kv-cache.md) | VRAM และ KV cache — คำนวณให้เป็น |
| [บทที่ 78](course/78-llm-architecture-internals.md) | สถาปัตยกรรม LLM ข้างใน — attention, MoE |
| [บทที่ 79](course/79-vllm-internals.md) | vLLM ข้างใน — PagedAttention, prefix cache |
| [บทที่ 48](course/48-serving-llm.md) | Serving LLM ให้เป็น API |
| [บทที่ 80](course/80-speculative-decoding.md) | Speculative Decoding |
| [บทที่ 81](course/81-serving-features.md) | Serving features — chat template, tool calling |
| [บทที่ 82](course/82-llm-evaluation.md) | ประเมินผลโมเดล LLM |
| [บทที่ 66](course/66-training-and-finetuning.md) | เทรนและ fine-tune ให้เป็น |
| [บทที่ 72](course/72-mlops.md) | MLOps — reproducibility และ registry |
| [บทที่ 49](course/49-gpu-on-containers-and-k8s.md) | แบ่ง GPU ให้หลายคนใช้ |
| [บทที่ 50](course/50-multi-gpu-and-networking.md) | หลาย GPU และเครือข่ายระหว่างการ์ด |
| [บทที่ 51](course/51-gpu-observability-and-cost.md) | วัดผล GPU และคิดต้นทุนให้เป็น |
| [บทที่ 83](course/83-gpu-kernels.md) | GPU Kernel และ FlashAttention |
| [บทที่ 84](course/84-quantization-and-numerics.md) | Quantization และ Numerics |
| [บทที่ 85](course/85-parallelism-and-disaggregation.md) | Parallelism ขั้นสูง — EP, disaggregation |
| [บทที่ 52](course/52-ai-system-security.md) | ความปลอดภัยของระบบ AI |

### ส่วนที่ 9 · คิดอย่างเป็นระบบ และก้าวต่อไป

| บท | เรื่อง |
|----|--------|
| [บทที่ 73](course/73-design-principles.md) | หลักการออกแบบโค้ด — SOLID, coupling |
| [บทที่ 74](course/74-software-architecture.md) | สถาปัตยกรรมซอฟต์แวร์ |
| [บทที่ 75](course/75-computation-theory.md) | ทฤษฎีการคำนวณภาคปฏิบัติ — Big-O, P/NP |
| [บทที่ 76](course/76-functional-programming.md) | Functional Programming ภาคปฏิบัติ |
| [บทที่ 77](course/77-system-design.md) | ออกแบบระบบจากศูนย์ |
| [บทที่ 60](course/60-grc-and-compliance.md) | ความเสี่ยง มาตรฐาน และการปฏิบัติตามกฎ |
| [บทที่ 61](course/61-digital-forensics.md) | Digital forensics |
| [บทที่ 62](course/62-anonymity-and-tunneling.md) | การระบุตัวตนบนอินเทอร์เน็ต — VPN, Tor, tunneling |
| [บทที่ 34](course/34-threat-modeling.md) | Threat modeling — คิดเองเป็น ไม่ใช่ท่อง checklist |
| [บทที่ 22](course/22-ethics-and-limits.md) | จริยธรรมและขอบเขต |
| [บทที่ 43](course/43-security-roles-and-paths.md) | งานสาย security ทำอะไรกันจริง ๆ |
| [บทที่ 44](course/44-ctf-and-legal-practice.md) | ฝึกอย่างถูกกฎหมาย — CTF และ bug bounty |
| [บทที่ 45](course/45-home-lab.md) | สร้างห้องแล็บของตัวเอง |
| [บทที่ 23](course/23-where-to-learn-more.md) | เรื่องพวกนี้เขาสอนกันในวิชาไหน |

### ภาคผนวก

| บท | เรื่อง |
|----|--------|
| [lab](lab/README.md) | Lab Server — สนามฝึกบนเครื่องคุณเอง |

## โครงสร้างโฟลเดอร์

```
.
├── README.md            ← คุณอยู่ตรงนี้
├── Makefile             ← คำสั่งลัด (make help)
├── _quarto.yml          ← ตั้งค่าหนังสือ (เว็บ / PDF / EPUB)
├── index.qmd            ← หน้าแรกของหนังสือ
├── course/              ← บทเรียน 85 บท
│   └── img/             ← รูปประกอบ SVG (รองรับธีมสว่าง/มืด)
└── lab/
    ├── server.py        ← lab server (stdlib ล้วน ไม่ต้องลงอะไร)
    ├── solve_pow.py     ← ตัวแก้โจทย์ PoW
    ├── db_demo.py       ← lab วัดผล N+1 / index / SELECT *
    ├── README.md        ← รายการ endpoint ทั้งหมด
    └── solutions/       ← เฉลยแบบฝึกหัด (ลองเองก่อนค่อยเปิด)
```

## ลำดับการเรียนที่แนะนำ

เลือกเส้นทางตามเป้าหมาย ไม่จำเป็นต้องอ่านเรียงเลข

**เส้นทาง A — ทำ API ให้ mobile app**
ส่วนที่ 1 → 2 → 3 แล้วหยิบเครื่องมือจากส่วนที่ 4 ตามต้องการ

**เส้นทาง B — automate เว็บที่มี CAPTCHA**
ส่วนที่ 1 → ส่วนที่ 5 → บทที่ 22 (จริยธรรม)

**เส้นทาง C — ความปลอดภัยของ API แบบเร่งด่วน**
(ถ้ามีเวลาแค่ครึ่งวัน และ API กำลังจะขึ้น production)
09 → **11** → **24** → 25 → แล้วเอา checklist ท้ายบทไปตรวจของจริง

**เส้นทาง D — เอาให้ครบ**
อ่านเรียงตามลำดับในสารบัญ (ไม่ใช่ตามเลขบท) แต่ละบทราว 20-40 นาที
รวมประมาณ 20-24 ชั่วโมง

> **เลขบทไม่เรียงตามลำดับการอ่าน** — เลขเป็นชื่อเรียกที่คงที่ (ทั้งเล่มอ้างอิงกันด้วยเลขนี้)
> ส่วนลำดับการอ่านจัดตามธีม ให้ดูจากสารบัญเป็นหลัก
>
> บทที่ห้ามข้ามถ้าทำ API: **11** (authentication) กับ **24** (authorization) —
> คนละเรื่องกัน และพลาดกันบ่อยทั้งคู่

## สิ่งที่ควรอ่านเพิ่ม

- [Everything curl](https://everything.curl.dev/) — หนังสือฟรีของผู้สร้าง curl เอง
- [MDN HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP) — reference ที่ดีที่สุดสำหรับ HTTP
- [ALTCHA docs](https://altcha.org/docs/) — เอกสาร ALTCHA
- [OWASP Anti-Automation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Bot_Management_and_Anti_Automation_Cheat_Sheet.html)
- [Playwright docs](https://playwright.dev/python/docs/intro)
