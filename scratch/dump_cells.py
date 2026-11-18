import json

def dump_notebook(path, out_path):
    with open(path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    with open(out_path, 'w', encoding='utf-8') as out:
        out.write(f"Notebook: {path}\n")
        out.write("="*60 + "\n\n")
        for i, cell in enumerate(nb.get('cells', [])):
            out.write(f"--- CELL {i} ({cell.get('cell_type')}) ---\n")
            source = "".join(cell.get('source', []))
            out.write(source + "\n\n")

dump_notebook('capstone-final/main_file_capstone(1).ipynb', 'scratch/dump_main_file_capstone.txt')
dump_notebook('capstone-final/satellitle_part.ipynb', 'scratch/dump_satellite_part.txt')
dump_notebook('capstone-final/florence_implementation (1).ipynb', 'scratch/dump_florence_implementation.txt')
print("Dumped notebooks.")
