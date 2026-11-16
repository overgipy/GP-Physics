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


def t_lc(ctx):
    pg = open_page(ctx, "lc-circuit", frozen=True)
    L, C, Q = 20e-3, 50e-6, 80e-6
    set_val(pg, "slL", 20); set_val(pg, "slC", 50); set_val(pg, "slQ", 80); set_val(pg, "slR", 0); step(pg, 47)
    T = 2 * math.pi * math.sqrt(L * C)
    check("LC 週期 T = 2π√(LC)（ms）", meter(pg, "週期 T"), T * 1e3, 0.001)
    check("LC 頻率 f（Hz）", meter(pg, "頻率 f"), 1 / T, 0.002)
    check("LC 總電磁能 = Q₀²/2C（任意時刻，μJ）", meter(pg, "總電磁能"), Q * Q / (2 * C) * 1e6, 0.003)
    check("LC 最大電流 ωQ₀（mA）", after("最大電流 ωQ₀ =", text(pg, "status")), Q / math.sqrt(L * C) * 1e3, 0.003)
    # 解析解本身：R = 0 時能量守恆、q 與 i 相差四分之一週期
    worst = pg.evaluate("""([L, C, Q]) => { let w = 0; const U = Q * Q / 2 / C, T = 2 * Math.PI * Math.sqrt(L * C);
        for (let k = 0; k < 400; k++) { const s = LabTest.lcState(L, C, 0, Q, k * T / 97); w = Math.max(w, Math.abs(s.q * s.q / 2 / C + L * s.i * s.i / 2 - U) / U); } return w; }""", [L, C, Q])
    check("LC 解析解能量守恆（最大相對偏差）", worst, 0, abs_=1e-9)
    quarter = pg.evaluate("([L, C, Q]) => LabTest.lcState(L, C, 0, Q, Math.PI / 2 * Math.sqrt(L * C))", [L, C, Q])
    check("LC t = T/4 時 q = 0", quarter["q"] / Q, 0, abs_=1e-9)
    check("LC t = T/4 時 |i| = ωQ₀", abs(quarter["i"]), Q / math.sqrt(L * C), 1e-9)
    # RLC：欠阻尼週期與臨界電阻
    set_val(pg, "slR", 20); step(pg, 10)
    w1 = math.sqrt(1 / (L * C) - (20 / (2 * L)) ** 2)
    check("RLC 欠阻尼週期 2π/ω′（ms）", after("2π／ω′ =", text(pg, "status")), 2 * math.pi / w1 * 1e3, 0.001)
    check("RLC 臨界電阻 2√(L/C)（Ω）", after("R c =|Rc =", text(pg, "status").replace("R c", "Rc")), 2 * math.sqrt(L / C), 0.003)
    num_ok = pg.evaluate("""([L, C, Q]) => { // 解析解 vs RK4
        const R = 20, T = 2 * Math.PI * Math.sqrt(L * C), n = 40000, dt = 2.3 * T / n; let q = Q, i = 0;
        const f = (q, i) => [i, -(R * i + q / C) / L];
        for (let k = 0; k < n; k++) { const a = f(q, i), b = f(q + a[0] * dt / 2, i + a[1] * dt / 2), c = f(q + b[0] * dt / 2, i + b[1] * dt / 2), d = f(q + c[0] * dt, i + c[1] * dt);
            q += dt / 6 * (a[0] + 2 * b[0] + 2 * c[0] + d[0]); i += dt / 6 * (a[1] + 2 * b[1] + 2 * c[1] + d[1]); }
        const s = LabTest.lcState(L, C, R, Q, 2.3 * T); return Math.abs(s.q - q) / Q; }""", [L, C, Q])
    check("RLC 解析解 vs RK4 數值積分（相對偏差）", num_ok, 0, abs_=1e-7)
    # 實驗：T²–LC 圖的斜率 = 4π²
    set_val(pg, "slR", 0); pg.uncheck("#chkNoise")
    for l, c in ((10, 10), (10, 40), (30, 40), (50, 60), (80, 90)):
        set_val(pg, "slL", l); set_val(pg, "slC", c); pg.click("#btnRec")
    check("LC 實驗 T²–LC 斜率 = 4π²", after("斜率 =", text(pg, "fitTxt")), 4 * math.pi ** 2, 0.002)
    # 未知電感：由 T²–C 斜率求 L，與揭曉值比較
    pg.click("#btnUnk")
    for c in (10, 30, 60, 90):
        set_val(pg, "slC", c); pg.click("#btnRec")
    est = after("斜率／4π² =", text(pg, "fitTxt")); pg.click("#btnRev")
    true_l = after("真正的電感是", text(pg, "fitTxt"))
    check("LC 未知電感：推算值 vs 揭曉值（mH）", est, true_l or -1, 0.01)
    # 電磁波
    pg.click('[data-m="em"]'); set_val(pg, "slLr", 200); set_val(pg, "slCr", 125); step(pg, 10)
    f = 1 / (2 * math.pi * math.sqrt(200e-6 * 125e-12))
    check("電磁波 f = 1/(2π√(LC))（MHz）", meter(pg, "頻率 f"), f / 1e6, 0.001)
    check("電磁波 λ = c/f（m）", meter(pg, "波長"), 2.998e8 / f, 0.001)
    pg.close()


def t_rigid(ctx):
    pg = open_page(ctx, "rigid-rotation", frozen=True)
    g, th, s_len = 9.8, 30, 2.0
    set_val(pg, "slTh", th); set_val(pg, "slS", s_len); set_val(pg, "slR", 4); set_val(pg, "slM", 0.8); step(pg, 6)
    shapes = (("sphere", 2 / 5, "實心球"), ("cyl", 1 / 2, "圓柱"), ("shell", 2 / 3, "空心球"), ("ring", 1.0, "圓環"), ("block", 0.0, "滑塊"))
    for sid, beta, name in shapes:
        set_val(pg, "selObj", sid); step(pg, 6)
        a = g * math.sin(math.radians(th)) / (1 + beta)
        check(f"滾動 {name} a = g sinθ/(1+β)", meter(pg, "質心加速度"), a, 0.001)
        check(f"滾動 {name} 到底時間 √(2s/a)", meter(pg, "到底時間"), math.sqrt(2 * s_len / a), 0.001)
        check(f"滾動 {name} I = βmR²（×10⁻³ kg·m²）", meter(pg, "轉動慣量"), beta * 0.8 * 0.04 ** 2 * 1e3, 0.002, 0.0006)
    # 質量、半徑不影響到底時間
    set_val(pg, "selObj", "sphere"); set_val(pg, "slR", 10); set_val(pg, "slM", 2); step(pg, 6)
    check("滾動 改變 m、R 後到底時間不變", meter(pg, "到底時間"), math.sqrt(2 * s_len * 1.4 / (g * 0.5)), 0.001)
    # 實際釋放：到底後平動＋轉動動能 = mgh，轉動占 β/(1+β)
    set_val(pg, "selSpd", 1); pg.click("#btnPlay"); step(pg, 200)
    kt, kr = meter(pg, "平動動能"), meter(pg, "轉動動能")
    check("滾動 力學能守恆 ½mv² + ½Iω² = mgs·sinθ", (kt or 0) + (kr or 0), 2 * g * s_len * 0.5, 0.002)
    check("滾動 實心球轉動動能占比 2/7", (kr or 0) / ((kt or 0) + (kr or 1e-9)), 2 / 7, 0.003)
    check("滾動 到底速度 √(2gs·sinθ/(1+β))", meter(pg, "質心速度"), math.sqrt(2 * g * s_len * 0.5 / 1.4), 0.003)
    # 與獨立的數值積分（牛頓第二定律＋力矩方程式，逐步積分）比較
    tnum = pg.evaluate("""() => { const beta = 2 / 3, th = 25 * Math.PI / 180, g = 9.8, s = 1.7; let d = 0, v = 0, w = 0, t = 0; const R = 0.05, dt = 1e-5;
        while (d < s) { // 未知數 a、f： m a = m g sinθ − f； (β m R²)(a/R) = f R
            const a = g * Math.sin(th) / (1 + beta), f = beta * a; v += (g * Math.sin(th) - f) * dt; w += f * R / (beta * R * R) * dt; d += v * dt; t += dt; }
        return [t, LabTest.rollTime(beta, 25, s), v - w * R]; }""")
    check("滾動 解析時間 vs 逐步積分", tnum[1], tnum[0], 1e-4); check("滾動 純滾動條件 v − ωR = 0", tnum[2], 0, abs_=1e-9)
    # 實驗：a–sinθ 圖求 β
    pg.uncheck("#chkNoise"); set_val(pg, "selObj", "shell")
    for ang in (10, 20, 30, 40):
        set_val(pg, "slTh", ang); pg.click("#btnRec")
    check("滾動 實驗反求 β（空心球 2/3）", after("斜率 − 1 =", text(pg, "fitTxt")), 2 / 3, 0.003)
    pg.click("#btnUnk")
    for ang in (10, 25, 40):
        set_val(pg, "slTh", ang); pg.click("#btnRec")
    est = after("斜率 − 1 =", text(pg, "fitTxt")); pg.click("#btnRev")
    m_ = re.search(r"β = [^=]*= (\d\.\d+)，誤差", text(pg, "fitTxt"))
    check("滾動 未知物體：推算 β vs 揭曉值", est, float(m_.group(1)) if m_ else -1, 0.01)
    # 模式 ②：角動量守恆與外力矩
    pg.click('[data-m="spin"]'); set_val(pg, "slW0", 2); set_val(pg, "slMd", 3); set_val(pg, "slI0", 1.2); step(pg, 6)
    I1 = 1.2 + 2 * 3 * 0.8 ** 2; L = I1 * 2
    check("轉盤 I = I₀ + 2mr²", meter(pg, "轉動慣量"), I1, 0.001)
    set_val(pg, "slRr", 0.2); step(pg, 6)
    I2 = 1.2 + 2 * 3 * 0.2 ** 2
    check("轉盤 收手臂後 ω₂ = I₁ω₁/I₂", meter(pg, "角速度"), L / I2, 0.002)
    check("轉盤 角動量不變", meter(pg, "角動量"), L, 0.001)
    check("轉盤 轉動動能 L²/2I₂", meter(pg, "轉動動能"), L * L / (2 * I2), 0.002)
    set_val(pg, "slTau", 2); l0 = meter(pg, "角動量"); step(pg, 6); t0 = num(text(pg, "runState")); l0 = meter(pg, "角動量"); step(pg, 120); t1 = num(text(pg, "runState")); l1 = meter(pg, "角動量")
    check("轉盤 外力矩 τ = ΔL/Δt", (l1 - l0) / (t1 - t0), 2, 0.03)
    pg.close()


def t_standing(ctx):
    pg = open_page(ctx, "standing-wave", frozen=True)
    # 弦：v = √(F/μ)，f_n = n v / 2L
    L, F, mu = 1.0, 25, 2.5e-3          # v = 100 m/s、f₁ = 50 Hz，共鳴頻率剛好落在滑桿刻度上
    set_val(pg, "slLs", L); set_val(pg, "slT", F); set_val(pg, "slMu", mu * 1e3); step(pg, 6)
    v = math.sqrt(F / mu)
    check("弦 波速 v = √(F/μ)", meter(pg, "波速"), v, 0.001)
    check("弦 基頻 f₁ = v/2L", meter(pg, "基頻"), v / (2 * L), 0.002)
    for n in (1, 2, 3, 5):
        set_val(pg, "slF", n * v / (2 * L)); step(pg, 6)
        check(f"弦 f = {n}·v/2L 時共鳴（相對振幅 %）", meter(pg, "相對振幅"), 100, 0.03)
        check(f"弦 n = {n} 時 L÷λ = n/2", meter(pg, "L ÷ λ"), n / 2, 0.003)
    set_val(pg, "slF", 1.5 * v / (2 * L)); step(pg, 6)
    check("弦 兩共鳴頻率的正中間振幅很小（%）", meter(pg, "相對振幅"), 6, 0.2)
    # 共鳴頻率不在滑桿刻度上時，「跳到共鳴頻率」按鈕仍要給精確值
    set_val(pg, "slLs", 1.5); set_val(pg, "slT", 36); set_val(pg, "slMu", 4); step(pg, 6)
    for n in (1, 2, 4):
        pg.click(f"#harmRow .chip:nth-of-type({n})"); step(pg, 6)
        check(f"弦 按鈕 n = {n}（f = {n}·√9000/3 Hz）共鳴（%）", meter(pg, "相對振幅"), 100, 0.005)
        check(f"弦 按鈕 n = {n} 時 L÷λ", meter(pg, "L ÷ λ"), n / 2, 0.001)
    # 閉管：f = (2n−1)v/4L；開管：f = n v/2L
    pg.click('[data-m="closed"]'); set_val(pg, "slTemp", 30); step(pg, 6)
    check("聲速 v = 331 + 0.6T（30°C）", meter(pg, "聲速"), 349, 0.001)
    set_val(pg, "slTemp", 20); set_val(pg, "slLp", 0.5); step(pg, 6)
    check("閉管 基頻 v/4L", meter(pg, "基頻"), 343 / 2, 0.002)
    for n in (1, 2, 3):
        check(f"閉管 第 {n} 個共鳴頻率 (2n−1)v/4L", pg.evaluate("n => LabTest.resFreq('closed', n, 343, 0.5)", n), (2 * n - 1) * 343 / 2, 1e-9)
        set_val(pg, "slF", round((2 * n - 1) * 343 / 2)); step(pg, 6)
        check(f"閉管 f = {(2 * n - 1)}f₁ 時共鳴（音量 %）", meter(pg, "音量"), 100, 0.03)
    set_val(pg, "slF", 343); step(pg, 6)
    check("閉管 2 倍頻不共鳴（音量 %）", meter(pg, "音量"), 6, 0.2)
    pg.click('[data-m="open"]'); set_val(pg, "slLp", 0.5); step(pg, 6)
    check("開管 基頻 v/2L（同管長為閉管的 2 倍）", meter(pg, "基頻"), 343, 0.002)
    set_val(pg, "slF", 686); step(pg, 6)
    check("開管 2 倍頻共鳴（音量 %）", meter(pg, "音量"), 100, 0.03)
    # 實驗：共鳴管測聲速（只看音量找共鳴點，不使用已知聲速）
    def scan_and_record():
        best, prev, rising = [], -1, False
        for mm in range(50, 1201, 2):
            set_val(pg, "slLp", mm / 1000); g = meter(pg, "音量")
            if g < prev:
                if rising and prev >= 85: best.append(mm - 2)
                rising = False
            elif g > prev: rising = True       # 相等（峰頂剛好落在兩個取樣點中間）時維持原狀態
            prev = g
        for mm in best:
            top = max(range(mm - 4, mm + 5), key=lambda x: (set_val(pg, "slLp", x / 1000), meter(pg, "音量"))[1])
            set_val(pg, "slLp", top / 1000); pg.click("#btnRec")
        return best
    pg.click('[data-m="closed"]'); pg.uncheck("#chkNoise"); set_val(pg, "slTemp", 20); pg.click('.chip.fork[data-f="512"]'); step(pg, 4)
    found = scan_and_record()
    check("共鳴管 512 Hz、120 cm 內的共鳴點數 (λ/4 的 1,3,5,7 倍)", len(found), 4, abs_=0)
    check("共鳴管 第 1 共鳴點 ≈ λ/4（mm）", found[0] if found else None, 343 / 512 / 4 * 1000, 0.03)
    check("共鳴管 由 Lₙ–n 斜率求聲速（20°C）", after("v = fλ =", text(pg, "fitTxt")), 343, 0.01)
    pg.click("#btnUnk"); pg.click('.chip.fork[data-f="1000"]'); step(pg, 4)
    scan_and_record(); dbg = text(pg, "fitTxt"); est = after("v = fλ =", dbg); pg.click("#btnRev")
    if est is None: print("      [除錯]", dbg, "|", text(pg, "recBody"), "|", text(pg, "tNote"))
    check("共鳴管 未知聲速：推算值 vs 揭曉值", est, after("真正的聲速是", text(pg, "fitTxt")) or -1, 0.01)
    # 管口修正 e = 0.6r：閉管 L + e = (2n−1)λ/4，開管 L + 2e = nλ/2
    pg.click("#btnUnk"); pg.check("#chkEnd"); set_val(pg, "slD", 5); set_val(pg, "slTemp", 20); pg.click('.chip.fork[data-f="512"]'); step(pg, 4)
    e = 0.6 * 0.025
    found = scan_and_record()
    check("管口修正 第 1 共鳴點 ≈ λ/4 − e（mm）", found[0] if found else None, (343 / 512 / 4 - e) * 1000, 0.02)
    check("管口修正 由斜率求聲速不受影響", after("v = fλ =", text(pg, "fitTxt")), 343, 0.01)
    check("管口修正 由截距求 e（cm）", after("管口修正 e =", text(pg, "fitTxt")), e * 100, 0.1)
    set_val(pg, "slLp", 0.5); step(pg, 6)
    check("管口修正 閉管基頻 v/4(L+e)", meter(pg, "基頻"), 343 / (4 * (0.5 + e)), 0.002)
    check("管口修正 有效長度 L + e（cm）", meter(pg, "有效長度"), (0.5 + e) * 100, 0.001)
    pg.click('[data-m="open"]'); step(pg, 6)
    check("管口修正 開管基頻 v/2(L+2e)", meter(pg, "基頻"), 343 / (2 * (0.5 + 2 * e)), 0.002)
    pg.click("#harmRow .chip:nth-of-type(2)"); step(pg, 6)
    check("管口修正 開管 n = 2 按鈕共鳴（音量 %）", meter(pg, "音量"), 100, 0.005)
    pg.uncheck("#chkEnd"); step(pg, 6)
    check("取消管口修正後 開管基頻回到 v/2L", meter(pg, "基頻"), 343, 0.002)
    pg.close()


def t_atwood(ctx):
    pg = open_page(ctx, "atwood", frozen=True)
    set_val(pg, "m1", 0.9); set_val(pg, "m2", 1.1); step(pg, 6)
    check("阿特午 a = (m₂−m₁)g/(m₁+m₂)", meter(pg, "加速度"), 0.2 * 9.8 / 2, 0.002)
    check("阿特午 T = 2m₁m₂g/(m₁+m₂)", meter(pg, "繩張力"), 2 * 0.9 * 1.1 * 9.8 / 2, 0.001)
    check("阿特午 時間 √(2h/a)", meter(pg, "所需時間"), math.sqrt(2 / 0.98), 0.001)
    set_val(pg, "selSpd", 1); pg.click("#btnPlay"); step(pg, 200)
    check("阿特午 釋放後末速 √(2ah)", meter(pg, "目前速度"), math.sqrt(2 * 0.98), 0.002)
    pg.uncheck("#chkNoise")
    for a, b in ((0.9, 1.1), (0.8, 1.2), (0.6, 1.4), (0.5, 2.0)):
        set_val(pg, "m1", a); set_val(pg, "m2", b); pg.click("#btnRec")
    check("阿特午 實驗斜率 = g", num(text(pg, "gFitVal")), 9.8, 0.003)
    set_val(pg, "selG", 1.62); pg.click("#btnClr")
    for a, b in ((0.9, 1.1), (0.5, 1.5)):
        set_val(pg, "m1", a); set_val(pg, "m2", b); pg.click("#btnRec")
    check("阿特午 月球斜率 = 1.62", num(text(pg, "gFitVal")), 1.62, 0.005)
    pg.click("#btnUnk")
    for a, b in ((0.9, 1.1), (0.5, 1.5)):
        set_val(pg, "m1", a); set_val(pg, "m2", b); pg.click("#btnRec")
    est = num(text(pg, "gFitVal")); pg.click("#btnRev")
    check("阿特午 未知星球：斜率 = 揭曉值", est, after("正確答案 g =", text(pg, "fitTxt")) or -1, 0.01)
    pg.click("#btnUnk"); set_val(pg, "selG", 9.8); pg.click('[data-m="tab"]')
    set_val(pg, "m1", 1.0); set_val(pg, "m2", 0.5); set_val(pg, "mu", 0.2); step(pg, 6)
    check("連體 a = (m₂−μm₁)g/(m₁+m₂)", meter(pg, "加速度"), 0.3 * 9.8 / 1.5, 0.002)
    check("連體 T = m₂(g−a)", meter(pg, "繩張力"), 0.5 * (9.8 - 1.96), 0.002)
    set_val(pg, "m2", 0.15); step(pg, 6)
    check("連體 拉不動時 a = 0", meter(pg, "加速度"), 0, abs_=1e-6)
    check("連體 拉不動時 T = m₂g", meter(pg, "繩張力"), 0.15 * 9.8, 0.002)


def t_elevator(ctx):
    pg = open_page(ctx, "elevator", frozen=True)
    set_val(pg, "m", 60); set_val(pg, "a", 2)
    for kind, t, a, name in (("up", 1, 2, "上樓啟動"), ("up", 3.5, 0, "上樓等速"), ("up", 6, -2, "上樓煞車"), ("down", 1, -2, "下樓啟動"), ("down", 6, 2, "下樓煞車"), ("fall", 0.6, -9.8, "自由落下")):
        pg.click(f'[data-k="{kind}"]'); pg.evaluate("t => LabTest.seek(t)", t); step(pg, 6)
        check(f"電梯 {name} N = m(g+a)", meter(pg, "磅秤讀數 N"), 60 * (9.8 + a), 0.001, 0.06)
    pg.click('[data-k="up"]'); pg.evaluate("LabTest.seek(3.5)"); step(pg, 6)
    check("電梯 等速段速度 v = a·t₁", meter(pg, "電梯速度"), 4, 0.003)
    k = pg.evaluate("LabTest.kin(7)")
    check("電梯 行程總位移 = v–t 圖面積", k[2], 0.5 * 4 * 2 * 2 + 4 * 3, 1e-6); check("電梯 到站速度為零", k[1], 0, abs_=1e-9)
    pg.click("#btnQ"); pg.evaluate("LabTest.seek(1)"); step(pg, 6)
    kgw = meter(pg, "公斤重"); est = 9.8 * (kgw - 60) / 60
    pg.fill("#ans", f"{est:.2f}"); pg.click("#btnA")
    check("電梯 挑戰：由讀數反推 a", est, num(text(pg, "chTrue")), 0.02)
    check("電梯 挑戰判定答對", 1.0 if "答對" in text(pg, "chRes") else 0.0, 1.0)


def t_kepler(ctx):
    pg = open_page(ctx, "kepler", frozen=True)
    for r0, k, M in ((1.0, 1.0, 1.0), (1.0, 1.25, 1.0), (1.5, 0.7, 2.0), (0.6, 1.3, 0.5)):
        set_val(pg, "r0", r0); set_val(pg, "k", k); set_val(pg, "M", M); step(pg, 6)
        a = r0 / (2 - k * k); T = math.sqrt(a ** 3 / M)
        check(f"克卜勒 r₀={r0} k={k} M={M} 半長軸", meter(pg, "半長軸"), a, 0.002)
        check(f"克卜勒 r₀={r0} k={k} M={M} 週期 T=√(a³/M)", meter(pg, "週期"), T, 0.002)
        sim = pg.evaluate("([a, b, c]) => LabTest.simulate(a, b, c)", [r0, k, M])
        check("　數值積分一圈的週期 = 第三定律", sim[0], T, 5e-4)
        check("　數值積分的另一端距離 = 2a − r₀", sim[1] if k >= 1 else sim[3], 2 * a - r0, 5e-4, 1e-4)
        check("　面積速率變化量（第二定律）", sim[2], 0, abs_=1e-6)
    set_val(pg, "r0", 1); set_val(pg, "k", 1); set_val(pg, "M", 1); step(pg, 6)
    check("克卜勒 地球軌道速率 ≈ 29.8 km/s", meter(pg, "速率"), 29.78, 0.005)
    set_val(pg, "k", 1.25); pg.click("#btnPlay"); step(pg, 240)
    check("克卜勒 播放中面積速率 = ½r₀v₀", meter(pg, "面積速率"), 0.5 * 1 * 1.25 * 2 * math.pi, 0.001)
    check("克卜勒 播放中力學能守恆", meter(pg, "力學能"), 4 * math.pi ** 2 * (1.25 ** 2 / 2 - 1), 0.002)
    set_val(pg, "k", 1.6); step(pg, 6)
    check("克卜勒 k > √2 為雙曲線", 1.0 if "雙曲線" in " ".join(t + v for t, v in meters(pg)) else 0.0, 1.0)
    pg.click("#btnUnk")
    for r0, k in ((1, 1), (1.5, 1.1), (0.8, 0.9), (1.2, 1.3)):
        set_val(pg, "r0", r0); set_val(pg, "k", k); pg.click("#btnRec")
    est = num(text(pg, "mFit")); pg.click("#btnRev")
    check("克卜勒 未知恆星：1/斜率 = 質量", est, num(text(pg, "mTrue")), 0.01)


def t_static(ctx):
    pg = open_page(ctx, "static-equilibrium", frozen=True)
    g = 9.8
    for i, v in (("mA", 40), ("xA", -1.5), ("mB", 60), ("xB", 1), ("p", 0), ("mb", 0)): set_val(pg, i, v)
    step(pg, 6)
    check("蹺蹺板 逆時針力矩 m_A g d_A", meter(pg, "逆時針力矩"), 40 * g * 1.5, 0.001); check("蹺蹺板 順時針力矩 m_B g d_B", meter(pg, "順時針力矩"), 60 * g * 1.0, 0.001)
    check("蹺蹺板 平衡時合力矩 = 0", meter(pg, "合力矩"), 0, abs_=0.06); check("蹺蹺板 支點支撐力 = 總重", meter(pg, "支點支撐力"), 100 * g, 0.001)
    set_val(pg, "p", 0.5); set_val(pg, "mb", 20); step(pg, 6)       # 支點移到 0.5，木板 20 kg（重心在 0）
    net = g * (40 * 2.0 + 20 * 0.5 - 60 * 0.5)
    check("蹺蹺板 移動支點＋木板自重 合力矩", meter(pg, "合力矩"), net, 0.001); check("蹺蹺板 系統重心 Σmx/Σm", meter(pg, "系統重心"), (40 * -1.5 + 60 * 1) / 120, 0.01, 0.001)
    pg.click("#btnQ"); step(pg, 4)
    mU = pg.evaluate("LabTest.hidden()"); set_val(pg, "xA", -1.0); set_val(pg, "mB", 50); step(pg, 4)
    best = min((abs(pg.evaluate("([m, x]) => LabTest.seesaw(LabTest.hidden(), -1, 50, x, 0, 0).net", [0, x / 100])), x / 100) for x in range(5, 201, 5))[1]
    est = 50 * best / 1.0
    check("蹺蹺板 挑戰：m_A = m_B d_B / d_A（位置解析度 5 cm）", est, mU, 0.03, 1.3)
    pg.click('[data-m="lad"]')
    for i, v in (("th", 60), ("d", 1), ("mp", 60), ("ml", 10), ("mu", 0.4)): set_val(pg, i, v)
    step(pg, 6); t = math.tan(math.radians(60)); nw = g * (5 + 60 * 1 / 4) / t
    check("梯子 N牆 = g(m梯/2 + m人 d/L)/tanθ", meter(pg, "牆的正向力"), nw, 0.001); check("梯子 N地 = 總重", meter(pg, "地面正向力"), 70 * g, 0.001)
    check("梯子 需要的 μ", meter(pg, "需要的摩擦係數"), nw / (70 * g), 0.003); dmax = 4 * (0.4 * 70 * t - 5) / 60
    check("梯子 最高可爬距離", meter(pg, "最高可爬距離"), dmax, 0.003)
    r = pg.evaluate("d => [LabTest.ladder(60, d - 0.01, 60, 10, 0.4).slip, LabTest.ladder(60, d + 0.01, 60, 10, 0.4).slip]", dmax)
    check("梯子 爬到臨界距離前後：不滑→滑", (0 if r[0] else 1) + (1 if r[1] else 0), 2, abs_=0)
    # 獨立驗算：對梯頂取力矩也要為零
    L, a = 4, math.radians(60); tau_top = 70 * g * L * math.cos(a) - nw * L * math.sin(a) - 60 * g * (L - 1) * math.cos(a) - 10 * g * 2 * math.cos(a)
    check("梯子 對梯頂的合力矩也為零", tau_top, 0, abs_=1e-6)


def t_efield(ctx):
    pg = open_page(ctx, "electric-field", frozen=True)
    k = 8.99e9; q = 2e-9
    set_val(pg, "q", 2)
    pg.evaluate("LabTest.set([[380, 200, 1]], [480, 200])"); step(pg, 6)       # 單一正電荷，探針在右方 10 cm
    check("點電荷 V = kQ/r", meter(pg, "電位"), k * q / 0.1, 0.002); check("點電荷 E = kQ/r²", meter(pg, "電場大小"), k * q / 0.01, 0.002)
    check("點電荷 電場方向向外（0°）", meter(pg, "電場方向"), 0, abs_=0.6)
    pg.evaluate("LabTest.set([[280, 200, 1], [480, 200, -1]], [380, 200])"); step(pg, 6)   # 電偶極中點
    check("電偶極 中點電位 = 0", meter(pg, "電位"), 0, abs_=0.06); check("電偶極 中點電場 = 2kQ/r²", meter(pg, "電場大小"), 2 * k * q / 0.01, 0.002)
    pg.evaluate("LabTest.probe([380, 100])"); step(pg, 6)                       # 中垂線上
    r = math.hypot(0.1, 0.1)
    check("電偶極 中垂線上電位 = 0", meter(pg, "電位"), 0, abs_=0.06); check("電偶極 中垂線上 E = 2kQ·cos45°/r²", meter(pg, "電場大小"), 2 * k * q / r ** 2 * (0.1 / r), 0.002)
    pg.evaluate("LabTest.set([[280, 200, 1], [480, 200, 1]], [380, 200])"); step(pg, 6)    # 兩正電荷中點
    check("兩正電荷 中點電場 = 0", meter(pg, "電場大小"), 0, abs_=0.06); check("兩正電荷 中點電位 = 2kQ/r", meter(pg, "電位"), 2 * k * q / 0.1, 0.002)
    g = pg.evaluate("""() => { LabTest.set([[250, 150, 2], [500, 260, -1]], [0, 0]); const h = 0.01, f = (x, y) => LabTest.field(x, y), e = f(400, 180);
        return [e[0], -(f(400 + h, 180)[2] - f(400 - h, 180)[2]) / (2 * h * 0.001), e[1], -(f(400, 180 + h)[2] - f(400, 180 - h)[2]) / (2 * h * 0.001)]; }""")
    check("E = −∇V（x 分量，數值微分）", g[0], g[1], 1e-4); check("E = −∇V（y 分量，數值微分）", g[2], g[3], 1e-4)
    # 試探電荷能量守恆
    pg.evaluate("LabTest.set([[280, 200, 1], [480, 200, -1]], [330, 150])"); pg.click("#btnGo"); step(pg, 3)
    e0 = meter(pg, "動能＋電位能"); step(pg, 40)
    check("試探電荷 動能＋電位能守恆", meter(pg, "動能＋電位能") or e0, e0, 0.01)
    pg.click('[data-m="paper"]'); set_val(pg, "V0", 6); pg.evaluate("LabTest.probe([380, 200])"); step(pg, 6)
    check("導電紙 平行電極中點電位 = V₀/2", meter(pg, "電位"), 3, 0.002); check("導電紙 E = V₀/d", meter(pg, "電場大小"), 6 / 0.4, 0.002)
    pg.click("#btnUnk")
    for x in (220, 300, 380, 460, 540): pg.evaluate("x => LabTest.probe([x, 200])", x); pg.click("#btnRec")
    est = num(text(pg, "vFit")); pg.click("#btnRev")
    check("導電紙 未知電壓：斜率 × d = V₀", est, num(text(pg, "vTrue")), 0.01)
    pg.click("#btnUnk"); pg.click('[data-e="point"]'); pg.evaluate("LabTest.probe([380, 90])"); step(pg, 6)
    check("導電紙 點電極中垂線電位 = V₀/2", meter(pg, "電位"), 3, 0.002)


def t_balance(ctx):
    pg = open_page(ctx, "current-balance", frozen=True)
    mu0 = 4e-7 * math.pi
    for i, v in (("Is", 3), ("I", 3), ("L", 3), ("n", 2000)): set_val(pg, i, v)
    step(pg, 6); B = mu0 * 2000 * 3; F = B * 3 * 0.03
    check("電流天平 B = μ₀nIs（mT）", meter(pg, "管內磁場"), B * 1000, 0.002); check("電流天平 F = ILB（×10⁻⁴ N）", meter(pg, "磁力"), F * 1e4, 0.002)
    check("電流天平 平衡砝碼 m = F/g（mg）", meter(pg, "平衡所需砝碼"), F / 9.8 * 1e6, 0.003)
    set_val(pg, "I", 1.5); step(pg, 6); check("電流天平 I 減半 → F 減半", meter(pg, "磁力"), F * 1e4 / 2, 0.002)
    set_val(pg, "Is", 1.5); step(pg, 6); check("電流天平 Is 也減半 → F 變 1/4", meter(pg, "磁力"), F * 1e4 / 4, 0.002)
    pg.click("#btnAuto"); step(pg, 6)
    check("電流天平 自動平衡後 mg ≈ F", meter(pg, "砝碼重量"), F * 1e4 / 4, 0.03)
    pg.uncheck("#chkNoise")
    for a, b in ((1, 2), (2, 3), (3, 4), (5, 5)): set_val(pg, "Is", a); set_val(pg, "I", b); pg.click("#btnRec")
    check("電流天平 實驗求 μ₀（×10⁻⁷）", num(text(pg, "muFit")), 4 * math.pi, 0.002)
    pg.click("#btnUnk")
    for a, b in ((1, 2), (2, 3), (3, 4), (5, 5)): set_val(pg, "Is", a); set_val(pg, "I", b); pg.click("#btnRec")
    est = num(text(pg, "nFit")); pg.click("#btnRev")
    check("電流天平 未知匝數", est, num(text(pg, "nTrue")), 0.005)


def t_transformer(ctx):
    pg = open_page(ctx, "transformer", frozen=True)
    for i, v in (("Np", 200), ("Ns", 400), ("Vp", 110), ("R", 100)): set_val(pg, i, v)
    step(pg, 6)
    check("變壓器 Vs = Vp·Ns/Np", meter(pg, "副線圈電壓"), 220, 0.001); check("變壓器 Is = Vs/R", meter(pg, "副線圈電流"), 2.2, 0.001)
    check("變壓器 Ip = Is·Ns/Np", meter(pg, "原線圈電流"), 4.4, 0.001); check("變壓器 輸入功率 = 輸出功率", meter(pg, "輸入功率"), meter(pg, "輸出功率"), 0.001)
    set_val(pg, "Ns", 50); step(pg, 6); check("變壓器 降壓 200:50", meter(pg, "副線圈電壓"), 27.5, 0.002)
    pg.check("#chkDC"); step(pg, 6); check("變壓器 直流電時 Vs = 0", meter(pg, "副線圈電壓"), 0, abs_=1e-9); pg.uncheck("#chkDC")
    pg.uncheck("#chkNoise"); pg.click("#btnUnk")
    for v in (40, 80, 120, 200): set_val(pg, "Vp", v); pg.click("#btnRec")
    est = num(text(pg, "nsFit")); pg.click("#btnRev")
    check("變壓器 未知線圈匝數", est, num(text(pg, "nsTrue")), 0.005)
    pg.click('[data-m="line"]')
    for i, v in (("P", 100), ("kV", 2), ("r", 4)): set_val(pg, i, v)
    step(pg, 6)
    check("輸電 I = P/V", meter(pg, "線路電流"), 50, 0.001); check("輸電 損失 I²r（kW）", meter(pg, "線路發熱"), 10, 0.001); check("輸電 效率", meter(pg, "輸電效率"), 90, 0.001); check("輸電 電壓降 Ir", meter(pg, "線路電壓降"), 200, 0.003)
    set_val(pg, "kV", 20); step(pg, 6)
    check("輸電 電壓升 10 倍 → 損失 1/100（kW）", meter(pg, "線路發熱"), 0.1, 0.005)
    set_val(pg, "kV", 0.5); step(pg, 6)
    check("輸電 0.5 kV 時電全耗在線路上", meter(pg, "用戶收到"), 0, abs_=1e-6)


def t_microwave(ctx):
    pg = open_page(ctx, "microwave", frozen=True)
    c0 = 2.998e8
    set_val(pg, "selF", 10.5); step(pg, 6); lam = c0 / 10.5e9 * 100
    check("微波 λ = c/f（cm）", meter(pg, "波長"), lam, 0.001)
    set_val(pg, "ti", 40); best = max(((pg.evaluate("a => LabTest.iRef(40, a)", a / 2), a / 2) for a in range(0, 181)))[1]
    check("微波 反射讀數最大處 θr = θi", best, 40, abs_=0.26)
    set_val(pg, "tr", 40); step(pg, 6); check("微波 θr = θi 時讀數 100", meter(pg, "接收器讀數"), 100, 0.001)
    pg.click('[data-m="std"]'); set_val(pg, "x", round(lam / 4, 2)); step(pg, 6)
    check("駐波 x = λ/4 為腹點", meter(pg, "接收器讀數"), 100, 0.002); check("駐波 節點間距 λ/2", meter(pg, "節點間距"), lam / 2, 0.001)
    # 獨立驗算：入射波＋反射波（反射時相位差 π）疊加後的時間平均強度
    v = pg.evaluate("""() => { const L = LabTest.lam(10.5), k = 2 * Math.PI / L, x = 1.0; let s = 0; const n = 2000;
        for (let i = 0; i < n; i++) { const wt = 2 * Math.PI * i / n, e = Math.sin(k * x + wt) - Math.sin(-k * x + wt); s += e * e; } return [s / n / 2 * 100, LabTest.iStd(x, 10.5)]; }""")
    check("駐波 兩行進波疊加的強度 = 4sin²(kx)·½", v[1], v[0], 1e-6)
    pg.click("#btnUnk"); fU = pg.evaluate("LabTest.hidden()"); h = c0 / (fU * 1e9) * 100 / 2
    n_max = int(12 / h)
    for n in range(1, min(n_max, 5) + 1): set_val(pg, "x", round(n * h / 0.02) * 0.02); pg.click("#btnRec")
    est = num(text(pg, "fFit")); pg.click("#btnRev")
    check("駐波 未知頻率（由節點間距）", est, fU, 0.01)
    pg.click('[data-m="pol"]')
    for a in (0, 30, 45, 60, 90):
        set_val(pg, "ph", a); step(pg, 6); check(f"偏振 φ={a}° 讀數 = 100cos²φ", meter(pg, "接收器讀數"), 100 * math.cos(math.radians(a)) ** 2, 0.002, 0.06)
    set_val(pg, "ph", 0); pg.check("#chkG")
    for a, want in ((0, 0), (90, 100), (45, 25)):
        set_val(pg, "al", a); step(pg, 6); check(f"偏振 柵欄 α={a}°（接收器不轉）", meter(pg, "接收器讀數"), want, 0.002, 0.06)
    set_val(pg, "al", 45); set_val(pg, "ph", 90); step(pg, 6)
    check("偏振 柵欄 45° 讓原本收不到的 φ=90° 重新收到 25", meter(pg, "接收器讀數"), 25, 0.002)


def t_decay(ctx):
    pg = open_page(ctx, "radioactive-decay", frozen=True)
    set_val(pg, "th", 10); set_val(pg, "selN", 1600); step(pg, 6)
    check("衰變 λ = ln2/T½", meter(pg, "衰變常數"), math.log(2) / 10, 0.003); check("衰變 起始活度 λN₀", meter(pg, "活度"), math.log(2) / 10 * 1600, 0.003)
    pg.evaluate("LabTest.seed(4242)")
    for k, frac in ((1, 0.5), (2, 0.25), (3, 0.125)):
        n = pg.evaluate("LabTest.run(10)"); step(pg, 6)
        check(f"衰變 第 {k} 個半衰期後剩下 ≈ N₀/{2 ** k}（3σ 內）", n, 1600 * frac, abs_=3 * math.sqrt(1600 * frac * (1 - frac)))
        check(f"衰變 第 {k} 個半衰期的理論值", meter(pg, "理論值"), 1600 * frac, 0.001)
    check("衰變 ln N–t 斜率求得半衰期（6% 內）", pg.evaluate("LabTest.fitHalf()"), 10, 0.06)
    pg.click("#btnFit"); check("衰變 頁面顯示的擬合半衰期", num(text(pg, "thFit")), 10, 0.06)
    # 無記憶性：撐過第一個半衰期的原子核，再過一個半衰期仍衰變一半
    r = pg.evaluate("() => { LabTest.seed(99); const a = LabTest.run(10), b = LabTest.run(10); return [a, b]; }")
    check("衰變 無記憶性：第二個半衰期衰變掉剩下的約一半", r[1] / r[0], 0.5, 0.08)
    pg.click('[data-n="碳-14,5730,年"]'); step(pg, 6)
    check("衰變 碳-14 半衰期 5730 年", meter(pg, "半衰期"), 5730, 0.001)
    pg.click("#btnUnk"); pg.evaluate("LabTest.seed(31337)"); thU = pg.evaluate("LabTest.hidden()"); pg.evaluate("t => LabTest.run(t)", thU * 4)
    pg.click("#btnFit"); est = num(text(pg, "thFit")); pg.click("#btnRev")
    check("衰變 未知核種半衰期（7% 內）", est, num(text(pg, "thTrue")), 0.07)


TESTS = {"shared": t_shared, "oscillation": t_oscillation, "projectile": t_projectile, "lens-mirror": t_lens,
         "calorimetry": t_calorimetry, "refraction": t_refraction, "doppler": t_doppler,
         "lc-circuit": t_lc, "rigid-rotation": t_rigid, "standing-wave": t_standing,
         "atwood": t_atwood,
         "elevator": t_elevator,
         "kepler": t_kepler,
         "static-equilibrium": t_static,
         "electric-field": t_efield,
         "current-balance": t_balance,
         "transformer": t_transformer,
         "microwave": t_microwave,
         "radioactive-decay": t_decay}


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
