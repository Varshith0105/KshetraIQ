import sys
import time
from pathlib import Path
import torch
import numpy as np
from PIL import Image

print("Testing SAM initialization...", flush=True)
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator

pth = Path("capstone-final/sam_vit_b_01ec64.pth")
print(f"Checkpoint exists: {pth.exists()}, size: {pth.stat().st_size if pth.exists() else 0}", flush=True)

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}", flush=True)

t0 = time.time()
sam = sam_model_registry["vit_b"](checkpoint=str(pth))
sam.to(device=device)
print(f"SAM loaded in {time.time()-t0:.2f}s", flush=True)

# Test generator with points_per_side=12, points_per_batch=16
mask_generator = SamAutomaticMaskGenerator(sam, points_per_side=12, points_per_batch=16)

# Test on 128x128 image
t1 = time.time()
img = np.zeros((128, 128, 3), dtype=np.uint8)
img[30:90, 30:90] = [50, 180, 50]
masks = mask_generator.generate(img)
print(f"Generated {len(masks)} masks in {time.time()-t1:.2f}s", flush=True)
