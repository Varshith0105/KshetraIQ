import json
import glob

def search_notebooks():
    for nb_path in glob.glob("capstone-final/*.ipynb"):
        with open(nb_path, "r", encoding="utf-8") as f:
            nb = json.load(f)
        print(f"\n=== Notebook: {nb_path} ===")
        for idx, cell in enumerate(nb.get("cells", [])):
            src = "".join(cell.get("source", []))
            outs = cell.get("outputs", [])
            out_txt = ""
            for o in outs:
                if "text" in o:
                    out_txt += "".join(o["text"])
            
            for term in ["class", "confusion", "resnet50", "matrix", "predict", "evaluate", "names", "labels"]:
                if term in src.lower() or term in out_txt.lower():
                    lines = [l for l in (src + "\n" + out_txt).splitlines() if term in l.lower()]
                    print(f"Cell {idx} mentions '{term}': {lines[:3]}")
                    break

search_notebooks()
