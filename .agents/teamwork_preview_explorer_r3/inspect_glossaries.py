import glob
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

for p in sorted(glob.glob('pages/*.py')):
    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    print(f"\n=======================================================")
    print(f"=== File: {p} ===")
    print(f"=======================================================")
    
    i = 0
    while i < len(lines):
        line = lines[i]
        if 'st.expander' in line and ('📖' in line or 'Guía' in line or 'Glosario' in line or 'Leyenda' in line or 'ℹ️' in line):
            print(f"\n--- Line {i+1}: {line.strip()} ---")
            expander_indent = len(line) - len(line.lstrip())
            j = i + 1
            exp_content = []
            while j < len(lines):
                cur_line = lines[j]
                if cur_line.strip() == '':
                    exp_content.append(cur_line)
                    j += 1
                    continue
                cur_indent = len(cur_line) - len(cur_line.lstrip())
                if cur_indent <= expander_indent and not cur_line.strip().startswith('#'):
                    break
                exp_content.append(cur_line)
                j += 1
            
            full_text = "".join(exp_content)
            print(full_text[:600] + ("..." if len(full_text) > 600 else ""))
            i = j - 1
        i += 1
