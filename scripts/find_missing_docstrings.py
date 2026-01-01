from pathlib import Path
import ast

root = Path('case_agent')
missing = []
for p in sorted(root.rglob('*.py')):
    try:
        src = p.read_text(encoding='utf-8')
        tree = ast.parse(src)
        if not (len(tree.body)>0 and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant) and isinstance(tree.body[0].value.value, str)):
            missing.append(str(p))
    except Exception as e:
        print('err', p, e)
print('\n'.join(missing))
