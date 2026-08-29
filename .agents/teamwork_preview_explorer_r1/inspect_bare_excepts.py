import ast
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
repo_root = Path(r"c:\Users\Administrator\Projets\RepubliCaraquistApp")

python_files = sorted(list(repo_root.glob("*.py")) + 
                      list(repo_root.glob("pages/*.py")) + 
                      list(repo_root.glob("utils/*.py")) + 
                      list(repo_root.glob("scripts/*.py")))

print("=== INSPECTING BARE EXCEPT HANDLERS ===")

for p in python_files:
    rel = str(p.relative_to(repo_root)).replace("\\", "/")
    with open(p, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
    
    with open(p, "r", encoding="utf-8-sig") as f:
        code = f.read()
    tree = ast.parse(code, filename=str(p))
    
    bare_excepts = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            bare_excepts.append(node.lineno)
            
    if bare_excepts:
        print(f"\n--- {rel} ({len(bare_excepts)} bare excepts) ---")
        for lineno in bare_excepts:
            # print surrounding lines
            start = max(0, lineno - 4)
            end = min(len(lines), lineno + 3)
            print(f"  Line {lineno}:")
            for idx in range(start, end):
                prefix = "  >> " if idx + 1 == lineno else "     "
                print(f"{prefix}{idx+1:4d}: {lines[idx].rstrip()}")

