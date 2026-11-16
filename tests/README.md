# 自動測試

用 Playwright（Python 版）以手機視窗（375px 寬、觸控）逐頁檢查網站。頁面一律用 `file://` 開啟，
所以同時也驗證了「離線、相對路徑可獨立開啟」。

## 安裝（只要一次）

```bash
pip install playwright pillow numpy
playwright install chromium
```

## 執行

```bash
python3 tests/run_all.py            # 冒煙測試＋公式回歸測試，全部跑一遍
python3 tests/smoke.py              # 逐頁：橫向溢出、console 錯誤、按鈕可點、canvas 有繪製、連結有效
python3 tests/smoke.py lc-circuit   # 只測指定單元
python3 tests/formulas.py           # 關鍵公式數值回歸（操作滑桿 → 讀頁面數值 → 與理論值比較）
```

## 改版前後的視覺比對

```bash
python3 tests/snapshot.py snap /tmp/before        # 改之前
# …修改程式…
python3 tests/snapshot.py snap /tmp/after         # 改之後
python3 tests/snapshot.py compare /tmp/before /tmp/after
```

`snapshot.py` 會用假時鐘把動畫固定在同一格，手機與桌機各存一張整頁截圖，
並記錄每個元素的計算後樣式；`compare` 逐像素、逐樣式屬性比對並列出差異。
（使用 p5.js 的四個單元動畫起始時間不完全可控，波形相位偶爾會差一格，重跑即可。）

## CDN

`diffraction`、`n-slit`、`photoelectric`、`refraction` 用 CDN 上的 p5.js，`elastic-collision` 用 Chart.js。
測試環境連不到 CDN 時，把 `p5.js`、`chart.umd.js` 放進一個資料夾，再設定環境變數：

```bash
TEST_VENDOR_DIR=/path/to/vendor python3 tests/run_all.py
```

## 新增單元時

1. 單元資料夾放好 `index.html` 後，`smoke.py` 會自動納入。
2. 在 `formulas.py` 加一個 `t_單元名(ctx)` 函式並登記到 `TESTS`，至少驗證該單元的核心公式。
