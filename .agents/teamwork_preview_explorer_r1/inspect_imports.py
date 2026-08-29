import ast
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
repo_root = Path(r"c:\Users\Administrator\Projets\RepubliCaraquistApp")

python_files = sorted(list(repo_root.glob("*.py")) + 
                      list(repo_root.glob("pages/*.py")) + 
                      list(repo_root.glob("utils/*.py")) + 
                      list(repo_root.glob("scripts/*.py")))

print("=== DETAILED INSPECTION OF IMPORTS ===")

for p in python_files:
    rel = str(p.relative_to(repo_root))
    with open(p, "r", encoding="utf-8") as f:
        code = f.read()
    lines = code.splitlines()
    tree = ast.parse(code, filename=str(p))
    
    # Check imports
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            # print if imports streamlit_app or other interesting things
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
                if any("streamlit_app" in n for n in names):
                    print(f"[{rel}:{node.lineno}] import {', '.join(names)}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if "streamlit_app" in mod or "utils" in mod:
                    names = [a.name for a in node.names]
                    print(f"[{rel}:{node.lineno}] from {mod} import {', '.join(names[:4])}{'...' if len(names)>4 else ''}")

