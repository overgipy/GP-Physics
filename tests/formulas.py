"""關鍵公式的數值回歸測試：實際操作頁面上的滑桿，讀出頁面顯示（或模擬量到）的數值，
與測試裡獨立計算的理論值比較。

用法： python3 tests/formulas.py            # 全部
       python3 tests/formulas.py oscillation doppler
"""
import sys, re, math
from common import *

RESULTS = []


def check(name, got, want, rel=0.01, abs_=0.0):
    ok = got is not None and abs(got - want) <= max(rel * abs(want), abs_)
    RESULTS.append(ok)
    g = "讀不到" if got is None else f"{got:.5g}"
    print(f"   {'✓' if ok else '✗'} {name}: 頁面 {g}　理論 {want:.5g}")
    return ok


def num(s):
    m = re.search(r"[-−]?\d+(?:\.\d+)?(?:e[-+]?\d+)?", (s or "").replace(",", ""))
    return float(m.group(0).replace("−", "-")) if m else None


def set_val(pg, id_, v):
    """設定滑桿或選單的值並觸發 input / change 事件。"""
    pg.evaluate("""([id, v]) => { const e = document.getElementById(id); e.value = v;
        e.dispatchEvent(new Event('input', { bubbles: true })); e.dispatchEvent(new Event('change', { bubbles: true })); }""", [id_, str(v)])


def meters(pg):
    """回傳 [(標題, 數值字串)]，同名儀表保留順序。"""
    return pg.evaluate("""() => [...document.querySelectorAll('.meter')].map(m => [m.querySelector('.meter-title').textContent.trim(),
        (m.querySelector('.meter-value').childNodes[0] || {}).textContent || ''])""")


def meter(pg, title, nth=0):
    hits = [v for t, v in meters(pg) if title in t]
    return num(hits[nth]) if len(hits) > nth else None


def text(pg, id_):
    return pg.evaluate("id => (document.getElementById(id) || {}).textContent || ''", id_)


def after(pattern, s):
    m = re.search(pattern + r"\s*([-−]?\d+(?:\.\d+)?)", s)
    return float(m.group(1).replace("−", "-")) if m else None


def agm(a, b):
    for _ in range(40):
        a, b = (a + b) / 2, math.sqrt(a * b)
    return a


# ---------------------------------------------------------------- 各單元
def t_oscillation(ctx):
    pg = open_page(ctx, "oscillation", frozen=True)
    m, k = 0.8, 40
    set_val(pg, "slM", m); set_val(pg, "slK", k); set_val(pg, "slA", 0.2); step(pg, 10)
    T = 2 * math.pi * math.sqrt(m / k)
    check("彈簧 T = 2π√(m/k)（顯示）", meter(pg, "T = 2π"), T, 0.002)
    pg.click("#btnReset"); pg.click("#btnPlay"); step(pg, 400)
    check("彈簧 T（由模擬量到）", meter(pg, "模擬量得"), T, 0.02)
    check("彈簧 總力學能 ½kA²", after("總力學能", text(pg, "status")), 0.5 * k * 0.2 ** 2, 0.01)
    # 單擺：大角度的精確週期 T = 2π√(L/g) / AGM(1, cos(θ0/2))
    pg.click('[data-m="pend"]')
    for L, th in ((1.0, 90), (0.5, 60), (1.5, 10)):
        set_val(pg, "slL", L); set_val(pg, "slTh", th); set_val(pg, "selG", 9.8); step(pg, 10)
        T0 = 2 * math.pi * math.sqrt(L / 9.8); Te = T0 / agm(1, math.cos(math.radians(th) / 2))
        check(f"單擺 大角度週期 L={L} θ₀={th}°（顯示）", after("精確週期", text(pg, "status")), Te, 0.002)
    set_val(pg, "slL", 1.0); set_val(pg, "slTh", 90); step(pg, 10)
    pg.click("#btnReset"); pg.click("#btnPlay"); step(pg, 600)
    check("單擺 θ₀=90° 週期（由模擬量到）", meter(pg, "模擬量得"), 2 * math.pi * math.sqrt(1 / 9.8) / agm(1, math.cos(math.pi / 4)), 0.02)
    pg.close()


def t_projectile(ctx):
    pg = open_page(ctx, "projectile", frozen=True)
    g = 9.8
    for v, a in ((25, 30), (30, 45), (18, 60)):
        set_val(pg, "slV", v); set_val(pg, "slA", a); set_val(pg, "slH", 0); set_val(pg, "slD", 0); step(pg, 10)
        s = text(pg, "status"); th = math.radians(a)
        check(f"拋射 射程 R = v₀²sin2θ/g（v₀={v}, θ={a}°）", after("射程", s), v * v * math.sin(2 * th) / g, 0.003, 0.06)
        check(f"拋射 飛行時間 2v₀sinθ/g", after("飛行時間", s), 2 * v * math.sin(th) / g, 0.005, 0.006)
        check(f"拋射 最大高度 v₀²sin²θ/2g", after("最大高度", s), (v * math.sin(th)) ** 2 / (2 * g), 0.005, 0.06)
    # 實際發射，落地時的水平位置應等於射程
    pg.click("#btnLaunch"); step(pg, 60 * 5)
    v, th = 18, math.radians(60)
    check("拋射 模擬落地位置 = 射程", meter(pg, "水平位置"), v * v * math.sin(2 * th) / g, 0.01)
    pg.close()


def t_lens(ctx):
    pg = open_page(ctx, "lens-mirror", frozen=True)
    for p, f in ((27, 9), (20, 8), (6, 10), (15, 10)):
        set_val(pg, "slF", f); set_val(pg, "slP", p); step(pg, 10)
        q = 1 / (1 / f - 1 / p)
        check(f"凸透鏡 1/p + 1/q = 1/f（p={p}, f={f}）像距", meter(pg, "像距"), q, 0.005, 0.06)
        check(f"凸透鏡 放大率 m = −q/p", meter(pg, "放大率"), -q / p, 0.01, 0.006)
    pg.close()


def t_calorimetry(ctx):
    pg = open_page(ctx, "calorimetry", frozen=True)
    cw, c_al = 4.18, 0.900       # J/(g·°C)
    for m1, T1, m2, T2 in ((100, 100, 200, 20), (300, 80, 150, 10), (500, 60, 50, 30)):
        set_val(pg, "selMat", "Al"); set_val(pg, "slM1", m1); set_val(pg, "slT1", T1); set_val(pg, "slM2", m2); set_val(pg, "slT2", T2); step(pg, 10)
        Tf = (m1 * c_al * T1 + m2 * cw * T2) / (m1 * c_al + m2 * cw)
        check(f"熱平衡 Tf（鋁 {m1} g {T1}°C＋水 {m2} g {T2}°C）", meter(pg, "平衡溫度"), Tf, 0.002, 0.06)
    pg.close()


def t_refraction(ctx):
    pg = open_page(ctx, "refraction")
    if not pg.evaluate("() => typeof window.p5 !== 'undefined'"):
        print("   ⚠ p5.js 沒載入（CDN 連不到），略過折射單元"); pg.close(); return
    for n1, n2 in ((1.5, 1.0), (2.42, 1.0), (1.33, 1.0), (1.5, 1.33)):
        set_val(pg, "sl_n1", n1); set_val(pg, "sl_n2", n2); pg.wait_for_timeout(120)
        check(f"臨界角 θc = sin⁻¹(n₂/n₁)（n₁={n1}, n₂={n2}）", num(text(pg, "val_critical")), math.degrees(math.asin(n2 / n1)), 0.002, 0.06)
    set_val(pg, "sl_n1", 1.0); set_val(pg, "sl_n2", 1.33); set_val(pg, "sl_angle", 40); pg.wait_for_timeout(120)
    check("司乃耳定律 n₁sinθ₁ = n₂sinθ₂（空氣→水 40°）", num(text(pg, "val_theta2")), math.degrees(math.asin(math.sin(math.radians(40)) / 1.33)), 0.003, 0.06)
    pg.close()


def t_doppler(ctx):
    pg = open_page(ctx, "doppler", frozen=True)
    for v, f0, vs in ((60, 3, 20), (80, 2, 30), (100, 5, 45)):
        set_val(pg, "slV", v); set_val(pg, "slF", f0); set_val(pg, "slVs", vs); step(pg, 10)
        check(f"都卜勒 波源接近 f′ = f₀·v/(v−vₛ)（v={v}, f₀={f0}, vₛ={vs}）", meter(pg, "公式", 0), f0 * v / (v - vs), 0.006, 0.006)
        check(f"都卜勒 波源遠離 f′ = f₀·v/(v+vₛ)", meter(pg, "公式", 1), f0 * v / (v + vs), 0.006, 0.006)
        check(f"都卜勒 前方視波長 λ′ = (v−vₛ)/f₀", meter(pg, "視波長", 0), (v - vs) / f0, 0.006, 0.06)
    pg.close()


def t_shared(ctx):
    """shared/lab.js 的工具函式。"""
    pg = ctx.new_page(); pg.goto(url("oscillation"))
    r = pg.evaluate("() => Lab.fitLine([[0, 1], [1, 3], [2, 5], [3, 7]])")
    check("Lab.fitLine 斜率", r["m"], 2, 1e-9); check("Lab.fitLine 截距", r["b"], 1, 1e-9)
    r = pg.evaluate("() => Lab.fitLineXY([{x:1,y:2.5},{x:2,y:5},{x:4,y:10}])")
    check("Lab.fitLineXY 斜率", r["m"], 2.5, 1e-9)
    check("Lab.fitThroughOrigin", pg.evaluate("() => Lab.fitThroughOrigin([[1, 3], [2, 6], [3, 9]])"), 3, 1e-9)
    for rng, n, want in ((10, 5, 2), (0.9, 4, 0.2), (37, 6, 5), (1200, 4, 500)):
        check(f"Lab.niceStep({rng}, {n})", pg.evaluate("([r, n]) => Lab.niceStep(r, n)", [rng, n]), want, 1e-9)
    check("Lab.rad(180)", pg.evaluate("() => Lab.rad(180)"), math.pi, 1e-12)
    pg.close()


TESTS = {"shared": t_shared, "oscillation": t_oscillation, "projectile": t_projectile, "lens-mirror": t_lens,
         "calorimetry": t_calorimetry, "refraction": t_refraction, "doppler": t_doppler}


def main():
    sel = [a for a in sys.argv[1:] if a in TESTS] or list(TESTS)
    with browser_context(mobile=True) as ctx:
        for name in sel:
            print(f"【{name}】")
            try:
                TESTS[name](ctx)
            except Exception as e:
                RESULTS.append(False); print(f"   ✗ 測試中斷：{str(e).splitlines()[0][:160]}")
    bad = RESULTS.count(False)
    print(f"\n公式回歸測試：{len(RESULTS) - bad}/{len(RESULTS)} 項通過")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
