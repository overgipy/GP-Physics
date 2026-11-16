"""逐頁冒煙測試（手機視窗 375px）：橫向溢出、console 錯誤、按鈕可點、canvas 有繪製、連結有效。

用法： python3 tests/smoke.py            # 全部頁面
       python3 tests/smoke.py oscillation projectile
"""
import sys, pathlib, re
from common import *

CANVAS_JS = """() => [...document.querySelectorAll('canvas')].map(c => {
  const r = c.getBoundingClientRect(); const vis = r.width > 4 && r.height > 4 && getComputedStyle(c).display !== 'none' && c.offsetParent !== null;
  let painted = null;
  try { const t = document.createElement('canvas'); t.width = 64; t.height = 64; const x = t.getContext('2d');
        x.drawImage(c, 0, 0, 64, 64); const d = x.getImageData(0, 0, 64, 64).data; const seen = new Set();
        for (let i = 0; i < d.length; i += 4) seen.add(d[i] + ',' + d[i+1] + ',' + d[i+2] + ',' + d[i+3]);
        painted = seen.size > 1; } catch (e) { painted = 'err:' + e.message; }
  return { id: c.id || c.className || '(無 id)', vis, painted, w: Math.round(r.width) }; })"""

OVERFLOW_JS = """() => { const de = document.documentElement; const w = window.innerWidth;
  const bad = []; if (de.scrollWidth > w + 1) { for (const e of document.querySelectorAll('body *')) {
    const r = e.getBoundingClientRect(); if (r.width && r.right > w + 1) { let p = e, clipped = false;
      while ((p = p.parentElement) && p !== document.body) { const o = getComputedStyle(p).overflowX; if (o !== 'visible') { clipped = true; break; } }
      if (!clipped) bad.push(e.tagName + (e.id ? '#' + e.id : '') + '.' + e.className + ' right=' + Math.round(r.right)); } } }
  return { scrollWidth: de.scrollWidth, innerWidth: w, bad: bad.slice(0, 5) }; }"""

BUTTONS_JS = """() => [...document.querySelectorAll('button, .mode-btn, .preset-btn, .chip')].map((b, i) => {
  b.setAttribute('data-test-i', i); const r = b.getBoundingClientRect();
  return { i, vis: r.width > 0 && r.height > 0 && getComputedStyle(b).visibility !== 'hidden', dis: !!b.disabled,
           w: Math.round(r.width), h: Math.round(r.height), label: (b.textContent || '').trim().slice(0, 14) }; })"""

HIT_JS = """i => { const b = document.querySelector('[data-test-i="' + i + '"]'); if (!b) return 'gone';
  b.scrollIntoView({ block: 'center', behavior: 'instant' }); const r = b.getBoundingClientRect(); if (!r.width || !r.height || b.disabled) return 'gone';
  const e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  return e && (e === b || b.contains(e) || e.contains(b)) ? 'ok' : 'covered by ' + (e ? e.tagName + '.' + e.className : 'null'); }"""


def check_page(ctx, page):
    fails, warns, errors = [], [], []
    pg = open_page(ctx, page, errors=errors)
    ov = pg.evaluate(OVERFLOW_JS)
    if ov["scrollWidth"] > ov["innerWidth"] + 1:
        fails.append(f"橫向溢出 scrollWidth={ov['scrollWidth']} > {ov['innerWidth']} {ov['bad']}")
    cvs = pg.evaluate(CANVAS_JS)
    for c in cvs:
        if c["vis"] and c["painted"] is not True:
            fails.append(f"canvas「{c['id']}」沒有繪製內容（{c['painted']}）")
    if page and not any(c["vis"] for c in cvs):
        warns.append("頁面上沒有可見的 canvas")
    btns = pg.evaluate(BUTTONS_JS)
    n_click = 0
    for b in btns:
        if not b["vis"] or b["dis"]:
            continue
        if b["h"] < 30:
            warns.append(f"按鈕「{b['label']}」高度只有 {b['h']}px（觸控偏小）")
        hit = pg.evaluate(HIT_JS, b["i"])
        if hit == "gone":
            continue
        if hit != "ok":
            fails.append(f"按鈕「{b['label']}」點不到：{hit}"); continue
        try:
            pg.locator(f'[data-test-i="{b["i"]}"]').click(timeout=1500); n_click += 1
        except Exception as e:
            # 點了前一顆之後這顆被隱藏或停用屬正常互動，不算失敗
            st = pg.evaluate("""i => { const b = document.querySelector('[data-test-i="' + i + '"]'); if (!b) return 'gone';
                 const r = b.getBoundingClientRect(); return (b.disabled || !r.width) ? 'hidden' : 'visible'; }""", b["i"])
            if st == "visible":
                fails.append(f"按鈕「{b['label']}」點擊失敗：{str(e).splitlines()[0][:80]}")
    pg.wait_for_timeout(300)
    ov2 = pg.evaluate(OVERFLOW_JS)
    if ov2["scrollWidth"] > ov2["innerWidth"] + 1:
        fails.append(f"操作後橫向溢出 scrollWidth={ov2['scrollWidth']} {ov2['bad']}")
    # 本地連結與資源
    for attr, sel in (("href", "a[href], link[href]"), ("src", "script[src]")):
        for v in pg.evaluate(f"() => [...document.querySelectorAll('{sel}')].map(e => e.getAttribute('{attr}'))"):
            if re.match(r"^(https?:|#|mailto:|javascript:)", v or "#"):
                continue
            target = (ROOT / page / v.split("#")[0].split("?")[0])
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                fails.append(f"連結失效：{v}")
    for e in errors:
        if "net::ERR" in e or "Failed to load resource" in e:
            warns.append("外部資源載入失敗（CDN？）：" + e[:90])
        else:
            fails.append(e[:200])
    pg.close()
    return fails, warns, n_click, len([c for c in cvs if c["vis"]])


def main():
    sel = arg_pages(sys.argv[1:])
    bad = 0
    with browser_context(mobile=True) as ctx:
        for p in sel:
            fails, warns, n, nc = check_page(ctx, p)
            name = p or "(首頁)"
            print(f"{'✗' if fails else '✓'} {name:28s} 按鈕 {n:3d} 顆、canvas {nc}")
            for f in fails: print("     ✗", f)
            for w in dict.fromkeys(warns): print("     ⚠", w)
            bad += bool(fails)
    print(f"\n冒煙測試：{len(sel) - bad}/{len(sel)} 頁通過")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
