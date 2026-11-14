import json
from pathlib import Path

nb_path = Path("E:/KshetraIQ/AgriVerse-AI/agriverse_ai.ipynb")
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

cells = nb.get("cells", [])

for i, cell in enumerate(cells):
    src = "".join(cell.get("source", []))
    if "ChatGroq" in src or "Groq(" in src or "sentence_transformers" in src or "Chroma(" in src or "GraphDatabase" in src:
        print(f"\n--- Cell {i} ---")
        for line in src.split("\n"):
            if any(k in line for k in ["ChatGroq", "Groq", "model", "temperature", "api_key", "HuggingFace", "neo4j", "bolt"]):
                print("  ", line.strip())

