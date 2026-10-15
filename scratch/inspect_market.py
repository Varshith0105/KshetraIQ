import json

with open("Agriverse_Models/Market_Price_Forecasting.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

for idx, cell in enumerate(nb.get("cells", [])):
    src = "".join(cell.get("source", []))
    outs = cell.get("outputs", [])
    print(f"\n==================== Market Price Cell {idx} ====================")
    print(src[:600])
    for o in outs:
        if "text" in o:
            print("--- Output ---")
            print("".join(o["text"])[:600])
