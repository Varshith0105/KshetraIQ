import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open("Agriverse_Models/Agriculture_AI_Integrated_System.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

for idx, cell in enumerate(nb.get("cells", [])):
    src = "".join(cell.get("source", []))
    if any(k in src.lower() for k in ["agriculture_ai_final", "final.pkl", "dump", "load", "model_dir"]):
        print(f"\n==================== Integrated Cell {idx} ====================")
        print(src[:600])
