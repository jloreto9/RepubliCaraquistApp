# Home.py - Redirección a 🏠_Home.py
import runpy
from pathlib import Path

home_file = Path(__file__).parent / "🏠_Home.py"
runpy.run_path(str(home_file), run_name="__main__")
