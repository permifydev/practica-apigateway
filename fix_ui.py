#!/usr/bin/env python
import os

# Read current file
path = 'sii_conect/src/components/ui.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace ft.padding.symmetric with ft.padding
content = content.replace('ft.padding.symmetric(vertical=10)', 'ft.padding(vertical=10)')
content = content.replace('ft.padding.symmetric(horizontal=10, vertical=3)', 'ft.padding(horizontal=10, vertical=3)')

# Write back
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed ui.py')