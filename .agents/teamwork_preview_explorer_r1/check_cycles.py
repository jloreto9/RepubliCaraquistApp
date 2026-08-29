import ast
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
repo_root = Path(r"c:\Users\Administrator\Projets\RepubliCaraquistApp")

print("=== CHECKING CIRCULAR IMPORTS & DEPENDENCY GRAPH ===")

# Build dependency graph between utils
import_graph = {}
for u in repo_root.glob("utils/*.py"):
    mod_name = u.stem
    import_graph[mod_name] = set()
    with open(u, "r", encoding="utf-8-sig") as f:
        code = f.read()
    tree = ast.parse(code, filename=str(u))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith("utils."):
                    import_graph[mod_name].add(a.name.split(".")[1])
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.startswith("utils."):
                import_graph[mod_name].add(mod.split(".")[1])
            elif mod.startswith("streamlit_app.utils."):
                import_graph[mod_name].add(mod.split(".")[-1])

print("Import graph within utils/:")
for mod, deps in sorted(import_graph.items()):
    print(f"  utils.{mod} imports: {sorted(list(deps))}")

# Check for cycles using DFS
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

cycles = find_cycles(import_graph)
print(f"\nDetected cycles in utils/: {len(cycles)}")
for c in cycles:
    print(f"  Cycle: {' -> '.join(c)}")

