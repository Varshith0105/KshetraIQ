import json

with open("Agriverse_Models/RL_Irrigation_Optimization.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

for idx, cell in enumerate(nb.get("cells", [])):
    src = "".join(cell.get("source", []))
    outs = cell.get("outputs", [])
    if any(k in src.lower() for k in ["env", "action", "observation", "step", "reward", "reset", "ppo", "save"]):
        print(f"\n==================== RL Cell {idx} ====================")
        print(src[:600])
        for o in outs:
            if "text" in o:
                print("--- Output ---")
                print("".join(o["text"])[:300])
