import json

with open("capstone-final/main_file_capstone(1).ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

with open("scratch/cell_out.txt", "w", encoding="utf-8") as f_out:
    for idx in range(len(nb.get("cells", []))):
        cell = nb["cells"][idx]
        src = "".join(cell.get("source", []))
        outs = cell.get("outputs", [])
        has_text = any("text" in o for o in outs)
        if has_text:
            f_out.write(f"\n==================== Cell {idx} ====================\n")
            f_out.write(src + "\n--- Output text ---\n")
            for o in outs:
                if "text" in o:
                    f_out.write("".join(o["text"]) + "\n")

print("Done writing to scratch/cell_out.txt")
