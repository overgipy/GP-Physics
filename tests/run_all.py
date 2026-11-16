"""一次跑完冒煙測試與公式回歸測試。用法： python3 tests/run_all.py"""
import subprocess, sys, pathlib
here = pathlib.Path(__file__).resolve().parent
codes = [subprocess.call([sys.executable, str(here / f)]) for f in ("smoke.py", "formulas.py")]
print("\n全部通過 ✓" if not any(codes) else "\n有測試失敗 ✗")
sys.exit(1 if any(codes) else 0)
