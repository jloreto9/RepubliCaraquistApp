import ast
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
repo_root = Path(r"c:\Users\Administrator\Projets\RepubliCaraquistApp")

python_files = sorted(list(repo_root.glob("*.py")) + 
                      list(repo_root.glob("pages/*.py")) + 
                      list(repo_root.glob("utils/*.py")) + 
                      list(repo_root.glob("scripts/*.py")))

print("=== CHECKING USAGE OF apply_plotly_theme ===")
for p in python_files:
    rel = str(p.relative_to(repo_root)).replace("\\", "/")
    with open(p, "r", encoding="utf-8-sig") as f:
        code = f.read()
    if "apply_plotly_theme" in code:
        print(f"File {rel} references apply_plotly_theme")
