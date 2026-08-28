--[[
  pdf-symbols.lua — แทนสัญลักษณ์/emoji ด้วยข้อความธรรมดา เฉพาะตอนสร้าง PDF

  ทำไมต้องมี:
    ฟอนต์ที่ใช้ใน LaTeX ไม่มี glyph ของ emoji (✅ ❌ ⚠ 🎉 …)
    ถ้าปล่อยไว้ LuaTeX จะพังทั้งเล่ม (selnolig ล้มตอนเจออักขระเหล่านี้)

  ทำเฉพาะ PDF — เว็บ (HTML) กับ EPUB ยังเห็น emoji เหมือนเดิม
  และไม่แตะไฟล์ต้นฉบับเลย
]]

if not FORMAT:match("latex") then
  return {}
end

-- เรียงจากลำดับที่ยาวที่สุดก่อน เพื่อให้ตัวที่มี variation selector ถูกจับก่อน
local REPLACEMENTS = {
  -- เครื่องหมายถูก/ผิด ที่ใช้เยอะที่สุดในคอร์ส
  { "\u{2705}",          "[OK]"  },  -- ✅
  { "\u{274C}",          "[X]"   },  -- ❌
  { "\u{26A0}\u{FE0F}",  "[!]"   },  -- ⚠️ (พร้อม variation selector)
  { "\u{26A0}",          "[!]"   },  -- ⚠
  { "\u{2713}",          "v"     },  -- ✓
  { "\u{2717}",          "x"     },  -- ✗
  { "\u{2611}",          "[x]"   },  -- ☑

  -- ลูกศรนำทาง
  { "\u{2B05}\u{FE0F}",  "<-"    },  -- ⬅️
  { "\u{2B05}",          "<-"    },  -- ⬅
  { "\u{27A1}\u{FE0F}",  "->"    },  -- ➡️
  { "\u{27A1}",          "->"    },  -- ➡
  { "\u{21B3}",          "->"    },  -- ↳
  { "\u{25B6}",          ">"     },  -- ▶
  { "\u{25C0}",          "<"     },  -- ◀
  { "\u{25BC}",          "v"     },  -- ▼

  -- หน้ายิ้มต่าง ๆ ใช้ประกอบอารมณ์ ตัดออกได้โดยไม่เสียความหมาย
  { "\u{1F389}",         ""      },  -- 🎉
  { "\u{1F631}",         "(!)"   },  -- 😱
  { "\u{1F616}",         ":-("   },  -- 😖
  { "\u{1F610}",         ":-|"   },  -- 😐
  { "\u{1F642}",         ":-)"   },  -- 🙂
  { "\u{1F512}",         "[lock]"},  -- 🔒
  { "\u{1F4B8}",         ""      },  -- 💸
  { "\u{1F511}",         "[key]" },  -- 🔑

  -- อื่น ๆ
  { "\u{25A1}",          "[ ]"   },  -- □
  { "\u{2122}",          "(TM)"  },  -- ™
  { "\u{FE0F}",          ""      },  -- variation selector ที่หลงเหลือ

  -- เส้นตารางในผัง ASCII: Tlwg Mono (ฟอนต์ mono ตัวเดียวที่มีภาษาไทย) ไม่มี glyph พวกนี้
  -- จึงแปลงเป็น ASCII ให้ยังพออ่านผังออกใน PDF
  -- ส่วนรูปประกอบตัวจริงเป็น SVG อยู่แล้ว จึงไม่กระทบความเข้าใจ
  { "\u{2500}",          "-"     },  -- ─
  { "\u{2550}",          "="     },  -- ═
  { "\u{2502}",          "|"     },  -- │
  { "\u{250C}",          "+"     },  -- ┌
  { "\u{2510}",          "+"     },  -- ┐
  { "\u{2514}",          "+"     },  -- └
  { "\u{2518}",          "+"     },  -- ┘
  { "\u{251C}",          "+"     },  -- ├
  { "\u{2524}",          "+"     },  -- ┤
  { "\u{252C}",          "+"     },  -- ┬
  { "\u{2534}",          "+"     },  -- ┴
  { "\u{253C}",          "+"     },  -- ┼
  { "\u{2588}",          "#"     },  -- █
  { "\u{2194}",          "<->"   },  -- ↔
  { "\u{2193}",          "v"     },  -- ↓
  { "\u{2191}",          "^"     },  -- ↑
  { "\u{2192}",          "->"    },  -- →
  { "\u{2190}",          "<-"    },  -- ←
}

local function convert(s)
  for _, pair in ipairs(REPLACEMENTS) do
    -- ใช้ plain find/replace (true = ไม่ตีความเป็น pattern)
    local from, to = pair[1], pair[2]
    local out, i = {}, 1
    while true do
      local a, b = s:find(from, i, true)
      if not a then break end
      out[#out + 1] = s:sub(i, a - 1)
      out[#out + 1] = to
      i = b + 1
    end
    if #out > 0 then
      out[#out + 1] = s:sub(i)
      s = table.concat(out)
    end
  end
  return s
end

return {
  {
    Str       = function(el) el.text = convert(el.text);  return el end,
    Code      = function(el) el.text = convert(el.text);  return el end,
    CodeBlock = function(el) el.text = convert(el.text);  return el end,
    RawInline = function(el) el.text = convert(el.text);  return el end,
    RawBlock  = function(el) el.text = convert(el.text);  return el end,
  }
}
