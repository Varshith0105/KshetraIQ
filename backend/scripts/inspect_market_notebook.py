import json
import sys

def analyze_notebook(path):
    with open(path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    print(f"Total cells: {len(nb.get('cells', []))}")
    for idx, cell in enumerate(nb.get('cells', [])):
        cell_type = cell.get('cell_type')
        source = "".join(cell.get('source', []))
        print(f"\n{'='*40} CELL {idx} [{cell_type.upper()}] {'='*40}")
        print(source.strip())
        outputs = cell.get('outputs', [])
        if outputs:
            print(f"\n--- Outputs ({len(outputs)}) ---")
            for o_idx, out in enumerate(outputs):
                out_type = out.get('output_type')
                print(f"[{out_type}]")
                if 'text' in out:
                    print("".join(out['text']).strip())
                elif 'data' in out:
                    if 'text/plain' in out['data']:
                        print("".join(out['data']['text/plain']).strip())
                elif 'name' in out and 'text' in out:
                    print(f"{out['name']}: {''.join(out['text']).strip()}")

if __name__ == '__main__':
    analyze_notebook('market-model-review/market-predection-analysis.ipynb')
