#!/usr/bin/env python3
"""
Remove HTML template strings from app.py and update to use render_template
"""

with open('/Users/rojdapolat_1/Documents/pdf/webapp/app.py', 'r') as f:
    lines = f.readlines()

# Find the start and end of template sections
in_template = False
new_lines = []
for i, line in enumerate(lines):
    # Skip lines that are HTML templates
    if "HOME_TEMPLATE = '''" in line or "TRAINING_TEMPLATE = '''" in line or "RESULT_TEMPLATE = '''" in line or "DATA_TEMPLATE = '''" in line:
        in_template = True
        continue
    
    if in_template:
        if line.strip().endswith("'''"):
            in_template = False
        continue
    
    # Skip HTML template comment section
    if "# HTML TEMPLATES" in line or "# ==========================================" in line:
        if i+1 < len(lines) and ('<html>' in lines[i+1] or '<link' in lines[i+1] or '<style>' in lines[i+1] or 'TEMPLATE' in lines[i+1]):
            continue
    
    # Skip standalone HTML lines (from broken templates)
    if line.strip().startswith(('<', '{%', '}}', '{% for', '{% if', '{% endif', '{% endfor', '{% set')):
        continue
    
    new_lines.append(line)

# Write back
with open('/Users/rojdapolat_1/Documents/pdf/webapp/app.py', 'w') as f:
    f.writelines(new_lines)

print(f"Cleaned app.py: {len(lines)} -> {len(new_lines)} lines")
