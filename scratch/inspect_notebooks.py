import json

def inspect_notebook(path):
    print(f"\n==================== {path} ====================")
    with open(path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    cells = nb.get('cells', [])
    print(f"Total cells: {len(cells)}")
    for i, cell in enumerate(cells):
        ctype = cell.get('cell_type')
        source = "".join(cell.get('source', []))
        lines = [l for l in source.strip().split('\n') if l.strip()]
        first_line = lines[0][:90] if lines else 'EMPTY'
        print(f"Cell {i:02d} [{ctype}]: {first_line}")

inspect_notebook('capstone-final/main_file_capstone(1).ipynb')
inspect_notebook('capstone-final/satellitle_part.ipynb')
inspect_notebook('capstone-final/florence_implementation (1).ipynb')
