import ast
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
repo_root = Path(r"c:\Users\Administrator\Projets\RepubliCaraquistApp")

pages = sorted(list(repo_root.glob("pages/*.py")))

print("=== CHECKING sys.path & IMPORTS IN pages/*.py ===")

for p in pages:
    rel = str(p.relative_to(repo_root)).replace("\\", "/")
    with open(p, "r", encoding="utf-8-sig") as f:
        code = f.read()
    has_sys_path = "sys.path.append" in code or "sys.path.insert" in code
    has_streamlit_fallback = "streamlit_app" in code
    print(f"Page: {rel:<40} | Has sys.path append: {str(has_sys_path):<5} | Has streamlit_app fallback: {str(has_streamlit_fallback):<5}")
