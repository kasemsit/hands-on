import torch, torch.nn as nn

def train_once(seed=None):
    if seed is not None:
        torch.manual_seed(seed)
    m = nn.Linear(100, 10)
    opt = torch.optim.SGD(m.parameters(), lr=0.1)
    x = torch.randn(32, 100)              # ← สุ่ม ถ้าไม่ตั้ง seed จะต่างทุกรอบ
    y = torch.randn(32, 10)
    for _ in range(20):
        opt.zero_grad()
        loss = ((m(x)-y)**2).mean()
        loss.backward(); opt.step()
    return round(loss.item(), 6)

print("=== ไม่ตั้ง seed — รัน 3 ครั้งได้ผลต่างกัน ===")
for i in range(3):
    print(f"  ครั้งที่ {i+1}: loss = {train_once()}")

print("\n=== ตั้ง seed=42 — รัน 3 ครั้งได้ผลเดิมเป๊ะ ===")
for i in range(3):
    print(f"  ครั้งที่ {i+1}: loss = {train_once(42)}")

print("\n=== สิ่งที่ต้องบันทึกเพื่อทำซ้ำได้ ===")
import sys, platform
print(f"  torch   : {torch.__version__}")
print(f"  python  : {sys.version.split()[0]}")
print(f"  cuda    : {torch.version.cuda}")
print(f"  platform: {platform.platform()[:40]}")
