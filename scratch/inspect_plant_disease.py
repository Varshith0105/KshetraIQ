import json

with open("capstone-final/main_file_capstone.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

with open("scratch/plant_disease_cells.txt", "w", encoding="utf-8") as out_f:
    for idx, cell in enumerate(nb.get("cells", [])):
        source = "".join(cell.get("source", []))
        outputs = cell.get("outputs", [])
        
        out_f.write(f"\n==================== Cell {idx} ====================\n")
        out_f.write(f"--- CODE ---\n{source}\n")
        for o_idx, out in enumerate(outputs):
            out_f.write(f"--- OUTPUT {o_idx} ---\n")
            if "text" in out:
                out_f.write("".join(out["text"]) + "\n")
            if "data" in out:
                for mime, val in out["data"].items():
                    if mime != "image/png":
                        out_f.write(f"[{mime}]: {str(val)[:300]}\n")
                    else:
                        out_f.write(f"[image/png]: {len(val)} base64 chars\n")

print("Wrote capstone-final/main_file_capstone.ipynb cells to scratch/plant_disease_cells.txt")
