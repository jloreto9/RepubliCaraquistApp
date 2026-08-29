import ast
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
repo_root = Path(r"c:\Users\Administrator\Projets\RepubliCaraquistApp")

python_files = sorted(list(repo_root.glob("*.py")) + 
                      list(repo_root.glob("pages/*.py")) + 
                      list(repo_root.glob("utils/*.py")) + 
                      list(repo_root.glob("scripts/*.py")))

print("=== CHECKING FULL REPOSITORY IMPORT GRAPH & CYCLES ===")

full_graph = {}
for p in python_files:
    rel = str(p.relative_to(repo_root)).replace("\\", "/")
    full_graph[rel] = set()
    with open(p, "r", encoding="utf-8-sig") as f:
        code = f.read()
    tree = ast.parse(code, filename=str(p))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                mod = a.name.replace(".", "/")
                # check if matches any local file
                for target in python_files:
                    t_rel = str(target.relative_to(repo_root)).replace("\\", "/")
                    if t_rel.startswith(mod) or t_rel == f"{mod}.py":
                        full_graph[rel].add(t_rel)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            mod_path = mod.replace(".", "/")
            if mod.startswith("streamlit_app."):
                mod_path = mod.replace("streamlit_app.", "").replace(".", "/")
            for target in python_files:
                t_rel = str(target.relative_to(repo_root)).replace("\\", "/")
                if t_rel == f"{mod_path}.py" or t_rel.startswith(f"{mod_path}/"):
                    full_graph[rel].add(t_rel)

print(f"Total nodes in graph: {len(full_graph)}")
for node, edges in sorted(full_graph.items()):
    print(f"  {node} -> {sorted(list(edges))}")

def find_cycles(graph):
    visited = set()
    stack = []
    cycles = []

    def dfs(node):
        visited.add(node)
        stack.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in stack:
                cycle = stack[stack.index(neighbor):] + [neighbor]
                cycles.append(cycle)
        stack.pop()

    for node in graph:
        if node not in visited:
            dfs(node)
    return cycles

cycles = find_cycles(full_graph)
print(f"\nDetected cycles in full repository: {len(cycles)}")
for c in cycles:
    print(f"  Cycle: {' -> '.join(c)}")
