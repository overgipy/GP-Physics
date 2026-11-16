"""李捷物理實驗室 — 測試共用工具（Playwright / Python）。

所有頁面都用 file:// 開啟，順便驗證「離線、相對路徑可獨立開啟」。
"""
import os, pathlib, sys
from contextlib import contextmanager
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
MOBILE = dict(viewport={"width": 375, "height": 740}, device_scale_factor=2,
              is_mobile=True, has_touch=True)
DESKTOP = dict(viewport={"width": 1280, "height": 900}, device_scale_factor=1)

# 可重現的亂數（截圖比對用）
SEED_JS = """(() => { let s = 123456789;
  Math.random = () => { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; return ((s >>> 0) % 1e9) / 1e9; }; })();"""

# 假時鐘：requestAnimationFrame / performance.now / Date.now 改由 __step(n) 一格一格推進（每格 1/60 秒）
FREEZE_JS = """(() => { let now = 1000, id = 0; const q = [];
  window.requestAnimationFrame = cb => { q.push([++id, cb]); return id; };
  window.cancelAnimationFrame = i => { const k = q.findIndex(x => x[0] === i); if (k >= 0) q.splice(k, 1); };
  performance.now = () => now; Date.now = () => 1.7e12 + now;
  window.__step = n => { for (let i = 0; i < n; i++) { now += 1000 / 60; for (const [, cb] of q.splice(0)) cb(now); } }; })();"""


def step(pg, frames):
    """推進假時鐘 frames 格（需以 frozen=True 開啟頁面）。"""
    pg.evaluate("n => window.__step(n)", frames)


# CDN 函式庫：若環境連不到 CDN，可用 TEST_VENDOR_DIR 指到放有 p5.js / chart.umd.js 的資料夾
VENDOR = {"p5.js": "p5.js", "chart.js": "chart.umd.js"}


def pages():
    """回傳所有單元頁（資料夾名），首頁以 '' 表示。"""
    ps = sorted(d.name for d in ROOT.iterdir()
                if d.is_dir() and (d / "index.html").exists() and d.name not in ("tests", "shared", "tools"))
    return [""] + ps


def url(page):
    return (ROOT / page / "index.html").as_uri()


def _route_cdn(ctx):
    vdir = os.environ.get("TEST_VENDOR_DIR")
    if not vdir:
        return
    def handler(route):
        u = route.request.url
        for key, fn in VENDOR.items():
            if key in u and (pathlib.Path(vdir) / fn).exists():
                return route.fulfill(path=str(pathlib.Path(vdir) / fn), content_type="text/javascript")
        route.abort()
    ctx.route(lambda u: u.startswith("http"), handler)


@contextmanager
def browser_context(mobile=True, seeded=False):
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(**(MOBILE if mobile else DESKTOP))
        _route_cdn(ctx)
        if seeded:
            ctx.add_init_script(SEED_JS)
        try:
            yield ctx
        finally:
            ctx.close(); b.close()


def open_page(ctx, page, frozen=False, errors=None):
    pg = ctx.new_page()
    if errors is not None:
        pg.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.on("dialog", lambda d: d.accept())
    if frozen:
        pg.add_init_script(FREEZE_JS)                 # 時間完全由測試控制
    pg.goto(url(page), wait_until="load")
    if frozen:
        # CSS 轉場不受假時鐘控制，關掉才能重現
        pg.add_style_tag(content="*,*::before,*::after{transition:none!important;animation:none!important;scroll-behavior:auto!important}")
        pg.wait_for_timeout(150)
        step(pg, 90)
    else:
        pg.wait_for_timeout(600)
    return pg


def arg_pages(argv):
    sel = [a for a in argv if not a.startswith("-")]
    allp = pages()
    if not sel:
        return allp
    return [("" if s in ("index", "home") else s.strip("/")) for s in sel]
