import py_compile
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
repo_root = Path(r"c:\Users\Administrator\Projets\RepubliCaraquistApp")

python_files = sorted(list(repo_root.glob("*.py")) + 
                      list(repo_root.glob("pages/*.py")) + 
                      list(repo_root.glob("utils/*.py")) + 
                      list(repo_root.glob("scripts/*.py")))

print("=== RUNNING py_compile.compile ON ALL FILES ===")
errors = []
for p in python_files:
    rel = str(p.relative_to(repo_root))
    try:
        py_compile.compile(str(p), doraise=True)
        print(f" [PASS] {rel}")
    except py_compile.PyCompileError as e:
        print(f" [FAIL] {rel}: {e}")
        errors.append((rel, e))

print(f"\nTotal compiled: {len(python_files)}, Errors: {len(errors)}")
