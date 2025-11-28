#!/usr/bin/env python3
"""
Remove PDF processing functions from app.py (they're now in pdf_processor.py)
"""

with open('/Users/rojdapolat_1/Documents/pdf/webapp/app.py', 'r') as f:
    content = f.read()

# Find where PDF functions start and end
start_marker = "# PDF PROCESSING FUNCTIONS"
end_marker = "# =========================================="

# Find the positions
start_pos = content.find(start_marker)
if start_pos == -1:
    start_marker = "# ==========================================" 
    start_pos = content.find(start_marker, content.find("df.to_csv"))
    if start_pos == -1:
        print("Could not find start marker")
        exit(1)

# Find where FLASK ROUTES section starts
flask_routes_pos = content.find("# FLASK ROUTES", start_pos)
if flask_routes_pos == -1:
    print("Could not find FLASK ROUTES marker")
    exit(1)

# Keep everything before PDF functions and after them
new_content = content[:start_pos] + content[flask_routes_pos:]

with open('/Users/rojdapolat_1/Documents/pdf/webapp/app.py', 'w') as f:
    f.write(new_content)

# Count lines
old_lines = len(content.split('\n'))
new_lines = len(new_content.split('\n'))
print(f"Removed PDF processing functions: {old_lines} -> {new_lines} lines ({old_lines - new_lines} lines removed)")
