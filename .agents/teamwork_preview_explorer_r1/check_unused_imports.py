import ast
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
repo_root = Path(r"c:\Users\Administrator\Projets\RepubliCaraquistApp")

python_files = sorted(list(repo_root.glob("*.py")) + 
                      list(repo_root.glob("pages/*.py")) + 
                      list(repo_root.glob("utils/*.py")) + 
                      list(repo_root.glob("scripts/*.py")))

print("=== CHECKING UNUSED IMPORTS ACROSS ALL FILES ===")

for p in python_files:
    rel = str(p.relative_to(repo_root)).replace("\\", "/")
    with open(p, "r", encoding="utf-8-sig") as f:
        code = f.read()
    tree = ast.parse(code, filename=str(p))
    
    # Collect all imported names and their aliases
    imports = [] # list of (imported_symbol, bound_name, lineno, is_from, mod)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                bound = a.asname or a.name.split(".")[0]
                imports.append((a.name, bound, node.lineno, False, ""))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for a in node.names:
                bound = a.asname or a.name
                imports.append((a.name, bound, node.lineno, True, mod))
    
    # Collect all Name and Attribute usage in AST (excluding the import nodes themselves)
    used_names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Name):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            # for module attributes like px.bar, pd.DataFrame
            curr = node
            while isinstance(curr, ast.Attribute):
                curr = curr.value
            if isinstance(curr, ast.Name):
                used_names.add(curr.id)
    
    # Also check string references in type annotations or __all__ or format strings
    unused = []
    for sym, bound, line, is_from, mod in imports:
        # If bound not in used_names
        if bound not in used_names:
            # check if in comments / docstrings or __all__
            unused.append((sym, bound, line, mod))
            
    if unused:
        print(f"\nFile: {rel}")
        for sym, bound, line, mod in unused:
            stmt = f"from {mod} import {sym}" if mod else f"import {sym}"
            print(f"  L{line:<4}: {stmt} (bound as '{bound}') is NOT referenced in file body")

