import ast
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
repo_root = Path(r"c:\Users\Administrator\Projets\RepubliCaraquistApp")

python_files = sorted(list(repo_root.glob("*.py")) + 
                      list(repo_root.glob("pages/*.py")) + 
                      list(repo_root.glob("utils/*.py")) + 
                      list(repo_root.glob("scripts/*.py")))

print("=== DEEP CODE STRUCTURE & PATTERNS ===")

for p in python_files:
    rel = str(p.relative_to(repo_root)).replace("\\", "/")
    with open(p, "r", encoding="utf-8-sig") as f:
        code = f.read()
    tree = ast.parse(code, filename=str(p))
    
    functions = []
    classes = []
    naked_excepts = []
    st_cache_decorators = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # check decorators
            decs = []
            for d in node.decorator_list:
                if isinstance(d, ast.Call):
                    if isinstance(d.func, ast.Attribute):
                        decs.append(f"{d.func.value.id if isinstance(d.func.value, ast.Name) else '?'}.{d.func.attr}")
                    elif isinstance(d.func, ast.Name):
                        decs.append(d.func.id)
                elif isinstance(d, ast.Attribute):
                    decs.append(f"{d.value.id if isinstance(d.value, ast.Name) else '?'}.{d.attr}")
                elif isinstance(d, ast.Name):
                    decs.append(d.id)
            functions.append((node.name, node.lineno, decs))
        elif isinstance(node, ast.ClassDef):
            classes.append((node.name, node.lineno))
        elif isinstance(node, ast.ExceptHandler):
            if node.type is None:
                naked_excepts.append(node.lineno)

    print(f"\nFile: {rel} (Lines: {len(code.splitlines())}, Functions: {len(functions)}, Classes: {len(classes)})")
    if classes:
        print(f"  Classes: {classes}")
    if functions:
        cached_funcs = [f"{name} (L{line}, decs={decs})" for name, line, decs in functions if any("cache" in d for d in decs)]
        if cached_funcs:
            print(f"  Cached functions: {cached_funcs}")
    if naked_excepts:
        print(f"  ⚠️ Naked except: handlers (bare except:) on lines: {naked_excepts}")

