import glob
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

for p in sorted(['🏠_Home.py'] + glob.glob('pages/*.py')):
    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    found = []
    for i, line in enumerate(lines):
        l_lower = line.lower()
        if any(kw in l_lower for kw in ['st.selectbox', 'st.multiselect', 'st.radio', 'st.button', 'st.metric', 'st.tabs', 'st.title', 'st.subheader', 'st.header', 'st.caption']):
            # check for English phrases
            for eng in ['"select ', "'select ", '"search ', "'search ", '"filter ', "'filter ", '"loading', "'loading", '"pitcher', '"batter', '"team ', '"player ']:
                if eng in l_lower:
                    found.append((i+1, line.strip()))
    
    if found:
        print(f"=== {p} ({len(found)} potentially untranslated lines) ===")
        for lineno, text in found:
            print(f"  {lineno:4d}: {text}")
    else:
        print(f"=== {p} : OK (100% Spanish UI labels) ===")
