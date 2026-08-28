#!/usr/bin/env python3
"""
ตรวจว่าบล็อก ```mermaid ทุกอันในคอร์สเขียนถูกไวยากรณ์

ทำไมต้องมี:
    Quarto ไม่ตรวจ mermaid ให้ตอน render — ถ้าเขียนผิด หน้าเว็บจะขึ้นรูป
    ระเบิดพร้อมคำว่า "Syntax error in text" แทนที่จะเป็นแผนภาพ
    และ build ก็ยังผ่านเป็นปกติ จึงไม่มีอะไรเตือนเลย

    สคริปต์นี้เอา mermaid.js ตัวจริงมารันใน headless Chrome
    แล้วเรียก mermaid.parse() กับทุกบล็อก

ใช้:
    python3 tools/check-mermaid.py          # ตรวจทั้งหมด
    python3 tools/check-mermaid.py course/04-cookies-sessions.md

กับดักที่เจอบ่อย:
    ;   ตัวจบคำสั่งของ mermaid  → เขียนเป็น #59;
    #   ตัวเริ่ม entity          → เขียนเป็น #35;

หมายเหตุ: สคริปต์นี้ตรวจแค่ "ไวยากรณ์" ไม่ได้ตรวจว่าข้อความล้นกล่องไหม
    เรื่องล้นกล่องเป็นปัญหาการจัดวาง ต้องดูด้วยตา — ที่เจอบ่อยคือ
    Note over X: ที่มีข้อความยาว ให้เปลี่ยนเป็น Note over X,Y: เพื่อให้กล่องกว้างขึ้น
"""

import html
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
MERMAID_JS = ROOT / "assets" / "mermaid" / "mermaid.min.js"

CHROME_CANDIDATES = [
    "google-chrome", "chromium", "chromium-browser",
    str(pathlib.Path.home() / ".local/share/quarto/chrome-headless-shell/"
        "linux64-*/chrome-headless-shell-linux64/chrome-headless-shell"),
]


def find_chrome() -> str | None:
    import glob
    import shutil
    for c in CHROME_CANDIDATES:
        if "*" in c:
            hits = glob.glob(c)
            if hits:
                return hits[0]
        elif shutil.which(c):
            return c
    return None


def extract_blocks(path: pathlib.Path) -> list[tuple[int, str]]:
    """คืน [(บรรทัดที่เริ่ม, ซอร์ส mermaid)] ของทุกบล็อกในไฟล์"""
    out = []
    text = path.read_text()
    for m in re.finditer(r"^```mermaid\n(.*?)^```", text, re.S | re.M):
        line_no = text[: m.start()].count("\n") + 1
        out.append((line_no, m.group(1)))
    return out


def build_page(blocks: list[dict]) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8"></head><body>
<div id="out"></div>
<script src="{MERMAID_JS.as_uri()}"></script>
<script>
mermaid.initialize({{startOnLoad:false, securityLevel:'loose'}});
const BLOCKS = {json.dumps(blocks, ensure_ascii=False)};
(async () => {{
  const results = [];
  for (const b of BLOCKS) {{
    try {{ await mermaid.parse(b.src); results.push({{...b, ok:true}}); }}
    catch (e) {{
      results.push({{...b, ok:false, err:String(e && e.message || e).split("\\n")[0]}});
    }}
  }}
  document.getElementById('out').textContent = JSON.stringify(results);
}})();
</script></body></html>"""


def main() -> int:
    if not MERMAID_JS.exists():
        print(f"ไม่พบ {MERMAID_JS} — คัดลอกมาจาก Quarto ก่อน", file=sys.stderr)
        return 2

    chrome = find_chrome()
    if not chrome:
        print("ไม่พบ Chrome/Chromium ในเครื่อง", file=sys.stderr)
        return 2

    if len(sys.argv) > 1:
        # รับได้ทั้ง path แบบสัมพัทธ์และแบบเต็ม
        files = [pathlib.Path(a).resolve() for a in sys.argv[1:]]
    else:
        files = sorted((ROOT / "course").glob("*.md"))

    blocks = []
    for f in files:
        if not f.exists():
            print(f"ไม่พบไฟล์: {f}", file=sys.stderr)
            return 2
        try:
            name = str(f.resolve().relative_to(ROOT))
        except ValueError:
            name = str(f)          # ไฟล์นอกโปรเจกต์ — ใช้ path เต็ม
        for line_no, src in extract_blocks(f):
            blocks.append({"file": name, "line": line_no, "src": src})

    if not blocks:
        print("ไม่พบบล็อก mermaid")
        return 0

    with tempfile.TemporaryDirectory() as td:
        page = pathlib.Path(td) / "check.html"
        page.write_text(build_page(blocks))
        proc = subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--no-sandbox",
             "--virtual-time-budget=20000", "--dump-dom", page.as_uri()],
            capture_output=True, text=True, timeout=180,
        )

    m = re.search(r'<div id="out">(.*?)</div>', proc.stdout, re.S)
    if not m:
        print("รัน Chrome ไม่สำเร็จ", file=sys.stderr)
        return 2

    results = json.loads(html.unescape(m.group(1)))
    bad = [r for r in results if not r["ok"]]

    for r in results:
        mark = "ok  " if r["ok"] else "FAIL"
        print(f"  {mark} {r['file']}:{r['line']}")
        if not r["ok"]:
            print(f"       {r['err']}")
            # ชี้กับดักที่พบบ่อยให้เลย
            if ";" in r["src"]:
                print("       ↳ มี ';' อยู่ในข้อความ — mermaid ถือเป็นตัวจบคำสั่ง"
                      " ให้เขียนเป็น #59; แทน")

    print(f"\nตรวจ {len(results)} บล็อก · ผ่าน {len(results)-len(bad)} · พัง {len(bad)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
