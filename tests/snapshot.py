"""視覺回歸工具：重構前後的截圖與「計算後樣式」比對。

用法： python3 tests/snapshot.py snap  輸出資料夾 [頁面…]
       python3 tests/snapshot.py compare 舊資料夾 新資料夾

做法：假時鐘（一格一格推進動畫）＋固定亂數種子，讓動畫畫面可重現；每頁在手機(375px)與桌機(1280px)
各存一張整頁截圖，並存下每個元素的 getComputedStyle（含 ::before/::after），
另外在「依序點過所有按鈕之後」再存一次（涵蓋 .active 等動態狀態）。
"""
import sys, json, gzip, pathlib, hashlib
from common import *

STYLE_JS = """() => { const out = []; const skip = new Set(['SCRIPT', 'STYLE', 'LINK', 'META', 'TITLE', 'HEAD']);
  const dump = (cs) => { const o = {}; for (const p of cs) o[p] = cs.getPropertyValue(p); return o; };
  let i = 0; for (const e of document.querySelectorAll('body, body *')) { if (skip.has(e.tagName)) continue;
    const key = (i++) + ' ' + e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (typeof e.className === 'string' && e.className ? '.' + e.className.trim().replace(/\\s+/g, '.') : '');
    const rec = { key, s: dump(getComputedStyle(e)) };
    for (const ps of ['::before', '::after']) { const c = getComputedStyle(e, ps); if (c.content && c.content !== 'none' && c.content !== 'normal') rec[ps] = dump(c); }
    out.push(rec); } return out; }"""

CLICK_JS = """() => [...document.querySelectorAll('button, .mode-btn, .preset-btn, .chip')].map((b, i) => { b.setAttribute('data-snap-i', i); return i; })"""


def snap(outdir, sel):
    out = pathlib.Path(outdir); out.mkdir(parents=True, exist_ok=True)
    for mobile in (True, False):
        tag = "m" if mobile else "d"
        with browser_context(mobile=mobile, seeded=True) as ctx:
            for p in sel:
                name = p or "index"
                pg = open_page(ctx, p, frozen=True)
                pg.screenshot(path=str(out / f"{name}.{tag}.png"), full_page=True)
                styles = {"load": pg.evaluate(STYLE_JS)}
                for i in pg.evaluate(CLICK_JS):
                    try:
                        pg.evaluate("""i => { const b = document.querySelector('[data-snap-i="' + i + '"]');
                            if (b && !b.disabled && b.getBoundingClientRect().width) b.click(); }""", i)
                        step(pg, 8)
                    except Exception:
                        pass
                pg.evaluate("() => document.querySelectorAll('[data-snap-i]').forEach(b => b.removeAttribute('data-snap-i'))")
                pg.wait_for_timeout(100); step(pg, 30)
                styles["clicked"] = pg.evaluate(STYLE_JS)
                pg.screenshot(path=str(out / f"{name}.{tag}.clicked.png"), full_page=True)
                with gzip.open(out / f"{name}.{tag}.styles.json.gz", "wt", encoding="utf8") as f:
                    json.dump(styles, f, ensure_ascii=False)
                pg.close()
                print("snap", tag, name, flush=True)


def img_diff(a, b):
    from PIL import Image, ImageChops
    import numpy as np
    A, B = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if A.size != B.size:
        return f"尺寸不同 {A.size} → {B.size}"
    d = np.asarray(ImageChops.difference(A, B)).max(axis=2)
    n = int((d > 8).sum())
    if n == 0:
        return None
    ys, xs = np.nonzero(d > 8)
    return f"{n} 個像素不同（{100 * n / d.size:.3f}%），範圍 x {xs.min()}–{xs.max()}、y {ys.min()}–{ys.max()}"


def compare(a, b):
    a, b = pathlib.Path(a), pathlib.Path(b)
    bad = 0
    for fb in sorted(b.glob("*.styles.json.gz")):      # 以新資料夾有的頁面為準（可分批比對）
        fa = a / fb.name
        name = fb.name.replace(".styles.json.gz", "")
        msgs = []
        if not fa.exists():
            print("–", name, "（舊資料夾沒有這一頁，略過）"); continue
        sa, sb = json.load(gzip.open(fa, "rt", encoding="utf8")), json.load(gzip.open(fb, "rt", encoding="utf8"))
        for state in sa:
            ea, eb = sa[state], sb[state]
            if len(ea) != len(eb):
                msgs.append(f"[{state}] 元素數量不同 {len(ea)} → {len(eb)}")
            nd = 0
            for x, y in zip(ea, eb):
                for part in ("s", "::before", "::after"):
                    dx, dy = x.get(part) or {}, y.get(part) or {}
                    diff = [(k, dx.get(k), dy.get(k)) for k in sorted(set(dx) | set(dy)) if dx.get(k) != dy.get(k)
                            and not (k.startswith('--') and dx.get(k) is None)]   # 共用檔多出來、該頁沒用到的顏色變數不算差異
                    if x["key"] != y["key"]:
                        diff.insert(0, ("(元素)", x["key"], y["key"]))
                    if diff:
                        nd += 1
                        if nd <= 4:
                            msgs.append(f"[{state}] {x['key'][:60]} {'' if part == 's' else part}: " + "; ".join(f"{k}: {u} → {v}" for k, u, v in diff[:4]))
            if nd > 4:
                msgs.append(f"[{state}] …共 {nd} 個元素樣式不同")
        for suffix in (".png", ".clicked.png"):
            r = img_diff(a / (name + suffix), b / (name + suffix))
            if r:
                msgs.append(f"截圖{suffix}: {r}")
        print(("✗ " if msgs else "✓ ") + name)
        for m in msgs: print("     ", m)
        bad += bool(msgs)
    print(f"\n比對結果：{bad} 個頁面視窗有差異" if bad else "\n比對結果：全部一致（計算後樣式與像素皆相同）")
    return bad


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "snap":
        snap(sys.argv[2], arg_pages(sys.argv[3:]))
    elif len(sys.argv) == 4 and sys.argv[1] == "compare":
        sys.exit(1 if compare(sys.argv[2], sys.argv[3]) else 0)
    else:
        print(__doc__)
