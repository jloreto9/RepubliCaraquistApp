import os
from pathlib import Path

repo_root = Path(r"c:\Users\Administrator\Projets\RepubliCaraquistApp")

print("=== CHECKING DIRECTORIES IN REPO ===")
for item in repo_root.iterdir():
    print(f" - {item.name} ({'DIR' if item.is_dir() else 'FILE'})")

tests_dir = repo_root / "tests"
print(f"Does tests/ directory exist? {tests_dir.exists()}")
