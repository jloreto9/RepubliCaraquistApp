import ast
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
repo_root = Path(r"c:\Users\Administrator\Projets\RepubliCaraquistApp")

python_files = sorted(list(repo_root.glob("*.py")) + 
                      list(repo_root.glob("pages/*.py")) + 
                      list(repo_root.glob("utils/*.py")) + 
                      list(repo_root.glob("scripts/*.py")))

print("=== DETAILED IMPORT & SYMBOL AUDIT ===")

# First, collect all exported/defined top-level functions, classes, and variables in utils/*.py
utils_symbols = {}
for u in repo_root.glob("utils/*.py"):
    mod_name = f"utils.{u.stem}"
    with open(u, "r", encoding="utf-8-sig") as f:
        code = f.read()
    tree = ast.parse(code, filename=str(u))
    defs = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defs.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defs.add(target.id)
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            defs.add(elt.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                defs.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            # If re-exporting
            if isinstance(node, ast.Import):
                for a in node.names:
                    defs.add(a.asname or a.name)
            elif isinstance(node, ast.ImportFrom):
                for a in node.names:
                    defs.add(a.asname or a.name)
    utils_symbols[mod_name] = defs
    print(f"Module {mod_name} defines {len(defs)} top-level symbols: {sorted(list(defs))[:5]}...")

print("\n=== CHECKING ALL IMPORTS ACROSS ALL FILES ===")
unresolved_imports = []
streamlit_app_usages = []

for p in python_files:
    rel = str(p.relative_to(repo_root))
    with open(p, "r", encoding="utf-8-sig") as f:
        code = f.read()
    tree = ast.parse(code, filename=str(p))

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            # Check for streamlit_app
            if "streamlit_app" in mod:
                streamlit_app_usages.append((rel, node.lineno, mod, [a.name for a in node.names]))
            
            # Check utils.* imports
            if mod.startswith("utils."):
                target_mod = mod
                if target_mod not in utils_symbols:
                    unresolved_imports.append((rel, node.lineno, f"Module '{mod}' does not exist in utils/"))
                else:
                    for a in node.names:
                        if a.name != "*" and a.name not in utils_symbols[target_mod]:
                            unresolved_imports.append((rel, node.lineno, f"Symbol '{a.name}' not found in {target_mod}"))

print(f"\n--- Streamlit_app Usages ({len(streamlit_app_usages)}) ---")
for rel, line, mod, names in streamlit_app_usages:
    print(f"  {rel}:{line} -> from {mod} import {', '.join(names)}")

print(f"\n--- Unresolved Local Imports ({len(unresolved_imports)}) ---")
for rel, line, err in unresolved_imports:
    print(f"  {rel}:{line} -> {err}")

