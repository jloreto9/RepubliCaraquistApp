import ast
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
repo_root = Path(r"c:\Users\Administrator\Projets\RepubliCaraquistApp")

python_files = sorted(list(repo_root.glob("*.py")) + 
                      list(repo_root.glob("pages/*.py")) + 
                      list(repo_root.glob("utils/*.py")) + 
                      list(repo_root.glob("scripts/*.py")))

print("=== CHECKING IMPORT PLACEMENT (TOP-LEVEL VS LATE/INSIDE FUNCTIONS) ===")

for p in python_files:
    rel = str(p.relative_to(repo_root)).replace("\\", "/")
    with open(p, "r", encoding="utf-8-sig") as f:
        code = f.read()
    tree = ast.parse(code, filename=str(p))
    
    late_imports = []
    function_imports = []
    
    for node in tree.body:
        # top level statement
        if not isinstance(node, (ast.Import, ast.ImportFrom, ast.Expr)) and not (isinstance(node, ast.Assign) and any(getattr(t, 'id', '') in ('__doc__', '__version__', '__all__') for t in getattr(node, 'targets', []))):
            pass

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            # check if inside function
            pass
            
    # Let's check non-top-level imports
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for sub in ast.walk(node):
                if isinstance(sub, (ast.Import, ast.ImportFrom)):
                    if isinstance(sub, ast.Import):
                        names = [a.name for a in sub.names]
                        function_imports.append((sub.lineno, node.name, f"import {', '.join(names)}"))
                    else:
                        names = [a.name for a in sub.names]
                        function_imports.append((sub.lineno, node.name, f"from {sub.module} import {', '.join(names)}"))

    # Also top-level imports that appear after function or class defs
    seen_def = False
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            seen_def = True
        elif isinstance(node, (ast.Import, ast.ImportFrom)) and seen_def:
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
                late_imports.append((node.lineno, f"import {', '.join(names)}"))
            else:
                names = [a.name for a in node.names]
                late_imports.append((node.lineno, f"from {node.module} import {', '.join(names)}"))

    if late_imports or function_imports:
        print(f"\nFile: {rel}")
        for lineno, stmt in late_imports:
            print(f"  - Late top-level import at L{lineno}: {stmt} (defined after functions/classes)")
        for lineno, func, stmt in function_imports:
            print(f"  - In-function import inside '{func}()' at L{lineno}: {stmt}")

