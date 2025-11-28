#!/usr/bin/env python3
"""
Remove SimpleDB class from app.py (it's now in database.py)
"""

with open('/Users/rojdapolat_1/Documents/pdf/webapp/app.py', 'r') as f:
    content = f.read()

# Find where class starts
class_start = content.find("# ==========================================\n    def __init__")
if class_start == -1:
    class_start = content.find("# DATABASE CLASS")
    if class_start == -1:
        print("Could not find SimpleDB class")
        exit(1)

# Find where FLASK ROUTES starts
flask_start = content.find("# FLASK ROUTES", class_start)
if flask_start == -1:
    print("Could not find FLASK ROUTES")
    exit(1)

# Keep everything before class and after it
new_content = content[:class_start] + content[flask_start:]

with open('/Users/rojdapolat_1/Documents/pdf/webapp/app.py', 'w') as f:
    f.write(new_content)

old_lines = len(content.split('\n'))
new_lines = len(new_content.split('\n'))
print(f"Removed SimpleDB class: {old_lines} -> {new_lines} lines ({old_lines - new_lines} lines removed)")
