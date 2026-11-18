import io
from pathlib import Path
from PIL import Image
import numpy as np

for path_str in [
    "scratch/sample_tomato_leaf.jpg",
    ".uploads/intelligence/plant_c007909e38744efdac0ed08758c7ca37/original.jpg",
    ".uploads/intelligence/plant_25218beecdee4310958e5a5135cb00ce/original.jpg",
]:
    p = Path(path_str)
    if p.exists():
        im = Image.open(p)
        arr = np.array(im)
        print(f"File: {p}")
        print(f"  Size: {im.size}, Mode: {im.mode}, Format: {im.format}, File size: {p.stat().st_size} bytes")
        print(f"  Unique colors: {len(np.unique(arr.reshape(-1, arr.shape[-1]), axis=0)) if arr.ndim==3 else len(np.unique(arr))}")
        print(f"  Mean RGB: {arr.mean(axis=(0,1)) if arr.ndim==3 else arr.mean()}")
