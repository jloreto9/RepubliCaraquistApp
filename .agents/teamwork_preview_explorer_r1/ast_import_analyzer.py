import os
import sys
import ast
import glob
from pathlib import Path

# Ensure UTF-8 stdout on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

repo_root = Path(r"c:\Users\Administrator\Projets\RepubliCaraquistApp")

python_files = sorted(list(repo_root.glob("*.py")) + 
                      list(repo_root.glob("pages/*.py")) + 
                      list(repo_root.glob("utils/*.py")) + 
                      list(repo_root.glob("scripts/*.py")))

print(f"=== Total Python files found: {len(python_files)} ===")
for p in python_files:
    print(f" - {p.relative_to(repo_root)}")

# 1. AST Syntax Check
print("\n=== 1. AST Syntax & Compilation Check ===")
ast_trees = {}
syntax_errors = []
for p in python_files:
    try:
        with open(p, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code, filename=str(p))
        ast_trees[p] = tree
        print(f" [PASS] {p.relative_to(repo_root)}")
    except Exception as e:
        print(f" [FAIL] {p.relative_to(repo_root)}: {e}")
        syntax_errors.append((p, e))

# 2. Extract Imports
print("\n=== 2. Detailed Import Analysis ===")
file_imports = {} # file -> list of (line, type, module, names)
for p, tree in ast_trees.items():
    rel = str(p.relative_to(repo_root))
    file_imports[rel] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                file_imports[rel].append({
                    "line": node.lineno,
                    "type": "import",
                    "module": alias.name,
                    "name": alias.asname or alias.name
                })
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names = [alias.name + (f" as {alias.asname}" if alias.asname else "") for alias in node.names]
            file_imports[rel].append({
                "line": node.lineno,
                "type": "from",
                "module": mod,
                "names": names,
                "level": node.level
            })

for rel, imps in file_imports.items():
    print(f"\nFile: {rel}")
    for imp in imps:
        if imp["type"] == "import":
            print(f"  L{imp['line']:<4}: import {imp['module']}")
        else:
            print(f"  L{imp['line']:<4}: from {'.' * imp.get('level', 0)}{imp['module']} import {', '.join(imp['names'])}")

# 3. Check requirements.txt vs 3rd party imports
print("\n=== 3. Requirements.txt vs Imported Packages ===")
req_file = repo_root / "requirements.txt"
req_packages = []
if req_file.exists():
    with open(req_file, "r", encoding="utf-8") as f:
        req_packages = [line.strip() for line in f if line.strip() and not line.startswith("#")]
print("requirements.txt contains:")
for r in req_packages:
    print(f"  {r}")

# Identify stdlib vs 3rd party vs local
stdlib_modules = sys.stdlib_module_names

all_imported_top_modules = set()
for rel, imps in file_imports.items():
    for imp in imps:
        mod = imp["module"].split(".")[0] if imp["module"] else ""
        if mod and imp.get("level", 0) == 0:
            all_imported_top_modules.add(mod)

local_modules = {"utils", "scripts", "pages", "Home", "app", "🏠_Home"}

print("\nCategorization of top-level imports:")
third_party_imports = {}
for top_mod in sorted(all_imported_top_modules):
    if top_mod in stdlib_modules:
        category = "STDLIB"
    elif top_mod in local_modules:
        category = "LOCAL"
    else:
        category = "THIRD_PARTY"
        # Find which files import it
        files_using = [rel for rel, imps in file_imports.items() if any((imp["module"] or "").split(".")[0] == top_mod for imp in imps)]
        third_party_imports[top_mod] = files_using
    print(f"  {top_mod:<20} -> {category}")

print("\nThird-party imports vs requirements.txt:")
for tp, using_files in third_party_imports.items():
    matched = False
    for r in req_packages:
        r_clean = r.split("==")[0].split(">=")[0].split("<=")[0].strip().lower().replace("-", "_")
        if tp.lower().replace("-", "_") == r_clean:
            matched = True
            break
        # Special mappings
        if tp == "statsapi" and "mlb_statsapi" in r_clean:
            matched = True
        if tp == "dotenv" and "python_dotenv" in r_clean:
            matched = True
        if tp == "supabase" and "supabase" in r_clean:
            matched = True
        if tp == "sklearn" and "scikit_learn" in r_clean:
            matched = True
    status = "DECLARED" if matched else "MISSING / UNDECLARED"
    print(f"  {tp:<15}: {status} (Used in {len(using_files)} files: {', '.join(using_files[:3])}{'...' if len(using_files)>3 else ''})")
