import json
from pathlib import Path

nb_path = Path("E:/KshetraIQ/AgriVerse-AI/agriverse_ai.ipynb")
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

cells = nb.get("cells", [])

# Let's inspect cells 96, 97, 98, 99, 100, 101, 102, 103, 118, 120, 121, 127, 129
for idx in [96, 97, 98, 99, 100, 101, 102, 103, 118, 120, 121, 127, 129]:
    if idx < len(cells):
        c = cells[idx]
        print(f"\n{'='*30} CELL {idx} [{c['cell_type']}] {'='*30}")
        src = "".join(c.get("source", []))
        print(src)

