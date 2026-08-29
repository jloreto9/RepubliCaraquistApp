import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
repo_root = Path(r"c:\Users\Administrator\Projets\RepubliCaraquistApp")

python_files = sorted(list(repo_root.glob("*.py")) + 
                      list(repo_root.glob("pages/*.py")) + 
                      list(repo_root.glob("utils/*.py")) + 
                      list(repo_root.glob("scripts/*.py")))

print("=== CHECKING FILE ENCODINGS & BOM ===")
for p in python_files:
    rel = str(p.relative_to(repo_root))
    with open(p, "rb") as f:
        raw = f.read()
    has_bom = raw.startswith(b'\xef\xbb\xbf')
    print(f"{rel:<45} | Size: {len(raw):<6} | UTF-8 BOM: {has_bom}")
