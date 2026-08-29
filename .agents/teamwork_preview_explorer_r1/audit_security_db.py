import ast
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
repo_root = Path(r"c:\Users\Administrator\Projets\RepubliCaraquistApp")

python_files = sorted(list(repo_root.glob("*.py")) + 
                      list(repo_root.glob("pages/*.py")) + 
                      list(repo_root.glob("utils/*.py")) + 
                      list(repo_root.glob("scripts/*.py")))

print("=== 1. CHECKING st.set_page_config ACROSS ALL FILES ===")
for p in python_files:
    rel = str(p.relative_to(repo_root)).replace("\\", "/")
    with open(p, "r", encoding="utf-8-sig") as f:
        code = f.read()
    if "set_page_config" in code:
        tree = ast.parse(code, filename=str(p))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "set_page_config":
                print(f"File {rel:<40} -> st.set_page_config() at L{node.lineno}")

print("\n=== 2. AUDITING SUPABASE MUTATION VS READ-ONLY ACCESS ===")
mutations = []
reads = []
for p in python_files:
    rel = str(p.relative_to(repo_root)).replace("\\", "/")
    with open(p, "r", encoding="utf-8-sig") as f:
        code = f.read()
    tree = ast.parse(code, filename=str(p))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if attr in ("insert", "upsert", "update", "delete"):
                mutations.append((rel, node.lineno, attr))
            elif attr == "select":
                reads.append((rel, node.lineno, attr))

print(f"Total Supabase SELECT queries found: {len(reads)}")
print(f"Total Supabase Mutation queries found: {len(mutations)}")
for rel, line, op in mutations:
    print(f"  ⚠️ Mutation: {rel}:{line} -> .{op}()")

print("\n=== 3. CREDENTIAL ACCESS & HARDCODED SECRETS AUDIT ===")
for p in python_files:
    rel = str(p.relative_to(repo_root)).replace("\\", "/")
    with open(p, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
    for idx, line in enumerate(lines, 1):
        if any(keyword in line for keyword in ["SUPABASE_KEY", "SUPABASE_URL", "OPENAI_API_KEY", "api_key", "password", "secret"]):
            # Check if it looks like a hardcoded key (e.g. quotes containing long base64/hex/jwt)
            if any(prefix in line for prefix in ["eyJ", "sk-", "sbp_"]):
                print(f"  🚨 HARDCODED CREDENTIAL FOUND: {rel}:{idx} -> {line.strip()}")
            elif "=" in line and not any(env_src in line for env_src in ["os.environ", "os.getenv", "st.secrets", "secrets.get", "environ.get", "dict", "def", "if", "assert", "#", "params", "headers", "args"]):
                print(f"  ⚠️ Suspicious line in {rel}:{idx} -> {line.strip()}")

