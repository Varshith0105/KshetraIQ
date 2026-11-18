import os
import time
from pathlib import Path
from PIL import Image
import torch

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from transformers import AutoProcessor, AutoModelForCausalLM

t0 = time.time()
print("Loading model...", flush=True)
proc = AutoProcessor.from_pretrained("florence-community/Florence-2-base", local_files_only=True, trust_remote_code=True)
mod = AutoModelForCausalLM.from_pretrained("florence-community/Florence-2-base", local_files_only=True, trust_remote_code=True)
print(f"Loaded in {time.time()-t0:.2f}s", flush=True)

im = Image.open("scratch/sample_tomato_leaf.jpg").convert("RGB")
inp = proc(text="<CAPTION>", images=im, return_tensors="pt")

t1 = time.time()
with torch.no_grad():
    out1 = mod.generate(**inp, max_new_tokens=50, num_beams=1)
txt1 = proc.batch_decode(out1, skip_special_tokens=True)[0]
print(f"num_beams=1 took {time.time()-t1:.2f}s: \"{txt1}\"", flush=True)

inp2 = proc(text="<MORE_DETAILED_CAPTION>", images=im, return_tensors="pt")
t2 = time.time()
with torch.no_grad():
    out2 = mod.generate(**inp2, max_new_tokens=80, num_beams=1)
txt2 = proc.batch_decode(out2, skip_special_tokens=True)[0]
print(f"num_beams=1 detailed took {time.time()-t2:.2f}s: \"{txt2}\"", flush=True)

