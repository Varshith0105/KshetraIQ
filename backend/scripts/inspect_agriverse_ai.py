import json
from pathlib import Path

nb_path = Path("E:/KshetraIQ/AgriVerse-AI/agriverse_ai.ipynb")
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

cells = nb.get("cells", [])

# Let's inspect agents, graph, and evaluation questions
target_cells = [61, 62, 63, 67, 68, 70, 118, 120, 122, 123, 125, 127, 129, 145, 146, 147, 148, 149]

for idx in target_cells:
    if idx < len(cells):
        c = cells[idx]
        print(f"\n{'='*30} CELL {idx} [{c['cell_type']}] {'='*30}")
        src = "".join(c.get("source", []))
        print(src[:2500])
