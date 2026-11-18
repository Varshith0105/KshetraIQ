import json

nb = json.load(open("capstone-final/main_file_capstone(1).ipynb", encoding="utf-8"))
for i, cell in enumerate(nb["cells"]):
    src = "".join(cell.get("source", []))
    if any(k in src for k in ["class_names", "train_data.class_names", "confusion_matrix"]):
        print(f"=== Cell {i} ===")
        print("Source excerpt:\n", src[:200])
        outputs = cell.get("outputs", [])
        for out in outputs:
            if "text" in out:
                print("Text output:\n", "".join(out["text"])[:300])
            elif "data" in out and "text/plain" in out["data"]:
                print("Data output:\n", "".join(out["data"]["text/plain"])[:300])
