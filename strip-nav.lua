--[[
  strip-nav.lua — ลบแถบนำทางท้ายบทตอนสร้าง Quarto book

  ไฟล์ .md แต่ละบทมีบรรทัดท้ายแบบนี้ไว้ให้กดอ่านต่อบน GitHub:

      ---
      [⬅ บทก่อน](04-....md) · [สารบัญ](../README.md) · [บทถัดไป ➡](06-....md)

  แต่ใน book/เว็บ Quarto มีปุ่มก่อนหน้า-ถัดไปกับสารบัญให้อยู่แล้ว
  ถ้าปล่อยไว้จะซ้ำซ้อน filter นี้จึงตัดทั้งเส้นคั่นและย่อหน้านั้นออก
  โดยไม่แตะไฟล์ต้นฉบับ (GitHub ยังเห็นลิงก์เหมือนเดิม)
]]

local stringify = pandoc.utils.stringify

--- ย่อหน้านี้เป็นแถบนำทางหรือเปล่า
local function is_nav(block)
  if block.t ~= "Para" and block.t ~= "Plain" then
    return false
  end
  local s = stringify(block)
  -- ต้องมีคำว่า "สารบัญ" และมีลูกศรนำทางอย่างน้อยหนึ่งข้าง
  return s:find("สารบัญ", 1, true) ~= nil
     and (s:find("บทก่อน", 1, true) ~= nil
       or s:find("บทถัดไป", 1, true) ~= nil
       or s:find("กลับหน้าสารบัญ", 1, true) ~= nil)
end

function Pandoc(doc)
  local out = {}
  local i = 1
  local blocks = doc.blocks

  while i <= #blocks do
    local b = blocks[i]
    local nxt = blocks[i + 1]

    -- รูปแบบ: HorizontalRule ตามด้วยย่อหน้านำทาง → ตัดทิ้งทั้งคู่
    if b.t == "HorizontalRule" and nxt ~= nil and is_nav(nxt) then
      i = i + 2
    elseif is_nav(b) then
      i = i + 1
    else
      table.insert(out, b)
      i = i + 1
    end
  end

  return pandoc.Pandoc(out, doc.meta)
end
