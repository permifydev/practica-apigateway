import os

base = 'sii_conect'
for root, dirs, files in os.walk(base):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            content = open(path).read()
            if 'page.session' in content:
                print(f'{path}: HAS page.session')