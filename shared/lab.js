/* 李捷物理實驗室 — shared/lab.js
   各單元共用的小工具（原本每頁各複製一份）。全部掛在全域物件 Lab 上，
   各頁在自己的程式開頭用  const { el, arrow, graph } = Lab;  取用。
   不依賴任何外部函式庫；用相對路徑 ../shared/lab.js 載入，離線也能開。 */
(function (global) {
    'use strict';

    /* ---------- DOM 與數學小工具 ---------- */
    const el = id => document.getElementById(id);
    const rad = d => d * Math.PI / 180;          // 度 → 弧度
    const deg = r => r * 180 / Math.PI;          // 弧度 → 度

    /* 座標軸的「漂亮刻度間距」：把 range 大約分成 n 格，回傳 1、2、5 × 10^k */
    function niceStep(range, n) {
        const raw = range / n, p = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / p;
        return (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * p;
    }
    /* 較早期單元使用的版本：固定約 5 格，門檻略有不同（保留以維持原本的刻度） */
    function niceStep5(range) {
        const t = range / 5, p = Math.pow(10, Math.floor(Math.log10(t))), n = t / p;
        return (n < 1.5 ? 1 : n < 3.5 ? 2 : n < 7.5 ? 5 : 10) * p;
    }

    /* 最小平方法直線擬合 y = m x + b。pts 為 [[x, y], …]；少於 2 點或 x 全相同時回傳 null */
    function fitLine(pts) {
        const n = pts.length; if (n < 2) return null;
        let sx = 0, sy = 0, sxx = 0, sxy = 0;
        pts.forEach(p => { sx += p[0]; sy += p[1]; sxx += p[0] * p[0]; sxy += p[0] * p[1]; });
        const d = n * sxx - sx * sx; if (Math.abs(d) < 1e-12) return null;
        const m = (n * sxy - sx * sy) / d, b = (sy - m * sx) / n;
        return { m, b };
    }
    /* 同上，但資料點是 [{x, y}, …] */
    function fitLineXY(pts) {
        const n = pts.length; if (n < 2) return null;
        const sx = pts.reduce((s, p) => s + p.x, 0), sy = pts.reduce((s, p) => s + p.y, 0),
            sxx = pts.reduce((s, p) => s + p.x * p.x, 0), sxy = pts.reduce((s, p) => s + p.x * p.y, 0);
        const den = n * sxx - sx * sx; if (Math.abs(den) < 1e-12) return null;
        const m = (n * sxy - sx * sy) / den;
        return { m, b: (sy - m * sx) / n };
    }
    /* 通過原點的直線擬合 y = m x（例如 T² 對 LC 作圖求比例常數） */
    function fitThroughOrigin(pts) {
        let sxx = 0, sxy = 0; pts.forEach(p => { sxx += p[0] * p[0]; sxy += p[0] * p[1]; });
        return sxx > 1e-300 ? sxy / sxx : null;
    }
    /* 模擬量測誤差：三角分布、範圍 ±amp */
    const noise = amp => (Math.random() + Math.random() - 1) * amp;

    /* ---------- Canvas 繪圖 ---------- */
    /* 箭頭（向量）。dash 給陣列時桿身畫虛線；長度小於 minLen 像素就不畫 */
    function arrow(ctx, x1, y1, x2, y2, color, w = 3, head = 10, dash = null, minLen = 2) {
        const len = Math.hypot(x2 - x1, y2 - y1); if (len < minLen) return;
        const a = Math.atan2(y2 - y1, x2 - x1), hl = Math.min(head, len * .6);
        ctx.save(); ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = w; ctx.lineCap = 'round';
        if (dash) ctx.setLineDash(dash);
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2 - Math.cos(a) * hl * .6, y2 - Math.sin(a) * hl * .6); ctx.stroke();
        if (dash) ctx.setLineDash([]);
        ctx.beginPath(); ctx.moveTo(x2, y2);
        ctx.lineTo(x2 - hl * Math.cos(a - .45), y2 - hl * Math.sin(a - .45));
        ctx.lineTo(x2 - hl * Math.cos(a + .45), y2 - hl * Math.sin(a + .45));
        ctx.closePath(); ctx.fill(); ctx.restore();
    }
    /* 粗體文字標籤，垂直置中 */
    function txt(ctx, s, x, y, color, size = 14, align = 'left') {
        ctx.save(); ctx.font = `bold ${size}px sans-serif`; ctx.fillStyle = color;
        ctx.textAlign = align; ctx.textBaseline = 'middle'; ctx.fillText(s, x, y); ctx.restore();
    }

    /* ---------- 儀表板 ---------- */
    /* 回傳一格儀表的 HTML（放進 .dashboard）。col 為數值顏色 */
    function meter(t, v, u, col = '#c3d0e4') {
        return `<div class="meter"><div class="meter-title">${t}</div><div class="meter-value" style="color:${col}">${v}<span class="unit">${u}</span></div></div>`;
    }
    /* 同上，但用 CSS class 指定顏色 */
    function meterClass(t, v, u, cl = '') {
        return `<div class="meter"><div class="meter-title">${t}</div><div class="meter-value ${cl}">${v}<span class="unit">${u}</span></div></div>`;
    }

    /* ---------- 通用 x–y 圖 ----------
       graph(canvas, { xmin, xmax, ymin, ymax, title, xl, yl,
                       series: [{ pts: [[x, y], …], col, w, dash, label }],
                       dots:   [{ x, y, col, r }],
                       vline:  x 位置畫一條黃色虛線, L: 左邊界寬度 })
       回傳 { PX, PY }：資料座標 → 像素座標，方便在圖上再加標記 */
    function graph(cv, o) {
        const x = cv.getContext('2d'), W = cv.width, H = cv.height, L = o.L || 62, R = 16, T = 30, B = 40, pw = W - L - R, ph = H - T - B;
        let { xmin, xmax, ymin, ymax } = o;
        if (xmax - xmin < 1e-12) xmax = xmin + 1;
        if (ymax - ymin < 1e-12) ymax = ymin + 1;
        const PX = v => L + (v - xmin) / (xmax - xmin) * pw, PY = v => T + ph - (v - ymin) / (ymax - ymin) * ph;
        x.fillStyle = '#0d121b'; x.fillRect(0, 0, W, H);
        const sx = niceStep(xmax - xmin, 6), sy = niceStep(ymax - ymin, 4),
            dx = Math.max(0, -Math.floor(Math.log10(sx) + 1e-9)), dy = Math.max(0, -Math.floor(Math.log10(sy) + 1e-9));
        x.font = '12px sans-serif';
        for (let v = Math.ceil(ymin / sy - 1e-9) * sy; v <= ymax + 1e-9; v += sy) {
            x.strokeStyle = Math.abs(v) < sy * 1e-6 ? '#3a4a66' : '#1b2433';
            x.beginPath(); x.moveTo(L, PY(v)); x.lineTo(L + pw, PY(v)); x.stroke();
            x.fillStyle = '#8a99ad'; x.textAlign = 'right'; x.fillText(v.toFixed(dy), L - 6, PY(v) + 4);
        }
        for (let v = Math.ceil(xmin / sx - 1e-9) * sx; v <= xmax + 1e-9; v += sx) {
            x.strokeStyle = Math.abs(v) < sx * 1e-6 ? '#3a4a66' : '#1b2433';
            x.beginPath(); x.moveTo(PX(v), T); x.lineTo(PX(v), T + ph); x.stroke();
            x.fillStyle = '#8a99ad'; x.textAlign = 'center'; x.fillText(v.toFixed(dx), PX(v), T + ph + 15);
        }
        x.save(); x.beginPath(); x.rect(L, T, pw, ph); x.clip();
        if (o.vline !== undefined) {
            x.strokeStyle = '#ffcc0088'; x.setLineDash([5, 4]);
            x.beginPath(); x.moveTo(PX(o.vline), T); x.lineTo(PX(o.vline), T + ph); x.stroke(); x.setLineDash([]);
        }
        (o.series || []).forEach(s => {
            if (!s.pts.length) return;
            x.strokeStyle = s.col; x.lineWidth = s.w || 2.4; x.setLineDash(s.dash || []);
            x.beginPath(); s.pts.forEach((p, i) => i ? x.lineTo(PX(p[0]), PY(p[1])) : x.moveTo(PX(p[0]), PY(p[1])));
            x.stroke(); x.setLineDash([]);
        });
        (o.dots || []).forEach(d => { x.fillStyle = d.col || '#ffcc00'; x.beginPath(); x.arc(PX(d.x), PY(d.y), d.r || 4, 0, 7); x.fill(); });
        x.restore();
        x.fillStyle = '#c3d0e4'; x.font = 'bold 13px sans-serif'; x.textAlign = 'left'; x.fillText(o.title || '', L, 18);
        let lx = L + pw; x.textAlign = 'right'; x.font = '12px sans-serif';
        (o.series || []).filter(s => s.label).reverse().forEach(s => {
            x.fillStyle = s.col; x.fillText('― ' + s.label, lx, 18); lx -= x.measureText('― ' + s.label).width + 12;
        });
        x.fillStyle = '#8a99ad'; x.font = '12px sans-serif'; x.textAlign = 'center'; x.fillText(o.xl || '', L + pw / 2, H - 5);
        x.save(); x.translate(13, T + ph / 2); x.rotate(-Math.PI / 2); x.fillText(o.yl || '', 0, 0); x.restore();
        return { PX, PY };
    }

    global.Lab = { el, rad, deg, niceStep, niceStep5, fitLine, fitLineXY, fitThroughOrigin, noise, arrow, txt, meter, meterClass, graph };
})(window);
