import json
import os
import glob
import re

print("Starting deep notebook and model audit...")

def inspect_notebook(path):
    print(f"\n==========================================")
    print(f"Inspecting Notebook: {path}")
    print(f"Size: {os.path.getsize(path)} bytes")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        cells = nb.get('cells', [])
        print(f"Total cells: {len(cells)}")
        code_cells = [c for c in cells if c.get('cell_type') == 'code']
        md_cells = [c for c in cells if c.get('cell_type') == 'markdown']
        print(f"Code cells: {len(code_cells)}, Markdown cells: {len(md_cells)}")
        
        # Search for key terms: classes, categories, target, read_csv, kaggle, keras, resnet, labels, ppo, etc.
        all_code = "\n".join("".join(c.get('source', [])) for c in code_cells)
        all_md = "\n".join("".join(c.get('source', [])) for c in md_cells)
        
        # Check imports
        imports = re.findall(r'(?:from|import)\s+([\w\.]+)', all_code)
        print(f"Key modules imported: {sorted(set(imports))[:20]}")
        
        # Check data loading
        read_matches = re.findall(r'(pd\.read_\w+\([^\)]+\))', all_code)
        if read_matches:
            print("Data loading calls:")
            for m in set(read_matches[:5]):
                print(f"  - {m}")
                
        # Look for class names, labels or targets
        class_matches = re.findall(r'(classes|class_names|labels|categories)\s*=\s*(\[[^\]]+\]|\{[^\}]+\})', all_code, re.IGNORECASE)
        if class_matches:
            print("Found class/label definitions:")
            for var, val in class_matches[:5]:
                print(f"  {var} = {val[:150]}...")
                
        # Check for pickle/model save calls
        save_matches = re.findall(r'(dump\([^\)]+\)|save_model\([^\)]+\)|\.save\([^\)]+\))', all_code)
        if save_matches:
            print("Save calls:")
            for s in set(save_matches[:5]):
                print(f"  - {s[:100]}")
                
    except Exception as e:
        print(f"Error reading {path}: {e}")

# Inspect capstone-final notebooks
for nb_file in glob.glob("capstone-final/*.ipynb"):
    inspect_notebook(nb_file)

# Inspect Agriverse_Models notebooks
for nb_file in glob.glob("Agriverse_Models/*.ipynb"):
    inspect_notebook(nb_file)

# Inspect AgriVerse-AI notebook
for nb_file in glob.glob("AgriVerse-AI/*.ipynb"):
    inspect_notebook(nb_file)

print("\nAudit completed.")
