import ast
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
repo_root = Path(r"c:\Users\Administrator\Projets\RepubliCaraquistApp")

python_files = sorted(list(repo_root.glob("*.py")) + 
                      list(repo_root.glob("pages/*.py")) + 
                      list(repo_root.glob("utils/*.py")) + 
                      list(repo_root.glob("scripts/*.py")))

print("=== 1. CHECKING USAGE OF ALL UTILS MODULES ===")
for u in repo_root.glob("utils/*.py"):
    mod_stem = u.stem
    references = []
    for p in python_files:
        if p == u:
            continue
        rel = str(p.relative_to(repo_root)).replace("\\", "/")
        with open(p, "r", encoding="utf-8-sig") as f:
            content = f.read()
        if mod_stem in content:
            references.append(rel)
    print(f"utils/{mod_stem}.py -> Referenced in {len(references)} files: {references}")

print("\n=== 2. CHECKING DUPLICATE & REDUNDANT IMPORTS IN EACH FILE ===")
for p in python_files:
    rel = str(p.relative_to(repo_root)).replace("\\", "/")
    with open(p, "r", encoding="utf-8-sig") as f:
        code = f.read()
    tree = ast.parse(code, filename=str(p))
    
    imported_names = [] # (name/alias, line, statement)
    for node in tree.body: # only top-level for now
        if isinstance(node, ast.Import):
            for a in node.names:
                imported_names.append((a.asname or a.name, node.lineno, f"import {a.name}"))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for a in node.names:
                imported_names.append((a.asname or a.name, node.lineno, f"from {mod} import {a.name}"))
    
    seen = {}
    duplicates = []
    for name, line, stmt in imported_names:
        if name in seen:
            duplicates.append((name, seen[name], line, stmt))
        else:
            seen[name] = line
    if duplicates:
        print(f"File: {rel}")
        for name, first_line, dup_line, stmt in duplicates:
            print(f"  - Symbol '{name}' first imported on L{first_line}, re-imported on L{dup_line} ({stmt})")

print("\n=== 3. REQUIREMENTS.TXT USAGE CHECK ===")
req_path = repo_root / "requirements.txt"
with open(req_path, "r", encoding="utf-8") as f:
    req_lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

all_code = ""
for p in python_files:
    with open(p, "r", encoding="utf-8-sig") as f:
        all_code += f"\n# --- {p.name} ---\n" + f.read()

for req in req_lines:
    pkg_name = req.split("==")[0].split(">=")[0].split("<=")[0].strip()
    # check how it's imported
    import_aliases = [pkg_name.lower().replace("-", "_")]
    if pkg_name.lower() == "mlb-statsapi":
        import_aliases = ["statsapi"]
    elif pkg_name.lower() == "python-dotenv":
        import_aliases = ["dotenv"]
    elif pkg_name.lower() == "scikit-learn":
        import_aliases = ["sklearn"]
    
    is_imported = False
    files_importing = []
    for p in python_files:
        with open(p, "r", encoding="utf-8-sig") as f:
            content = f.read()
        for alias in import_aliases:
            if f"import {alias}" in content or f"from {alias}" in content:
                is_imported = True
                files_importing.append(str(p.relative_to(repo_root)).replace("\\", "/"))
                break
    
    pinned = "==" in req
    print(f"Package: {req:<20} | Pinned: {str(pinned):<5} | Used in code: {str(is_imported):<5} ({len(files_importing)} files: {', '.join(files_importing[:3])})")

