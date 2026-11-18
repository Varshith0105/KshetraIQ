import os
import sys
import time

# Set offline mode if cached to avoid network retries inside sandbox
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import torch
from PIL import Image
import numpy as np

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}", flush=True)

test_img = Image.new("RGB", (224, 224), color=(34, 139, 34))

# Test BLIP
print("\n--- Testing BLIP ---", flush=True)
try:
    from transformers import BlipProcessor, BlipForConditionalGeneration
    t0 = time.time()
    blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base", local_files_only=True)
    blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base", local_files_only=True).to(device)
    print(f"BLIP loaded in {time.time()-t0:.2f}s", flush=True)

    inputs = blip_processor(images=test_img, return_tensors="pt").to(device)
    with torch.no_grad():
        out = blip_model.generate(**inputs, max_new_tokens=30)
    caption = blip_processor.decode(out[0], skip_special_tokens=True)
    print(f"BLIP Caption: {caption}", flush=True)
except Exception as e:
    print(f"BLIP Error: {e}", flush=True)

# Test Florence-2
print("\n--- Testing Florence-2 ---", flush=True)
try:
    from transformers import AutoProcessor, AutoModelForCausalLM
    t0 = time.time()
    try:
        from transformers import Florence2ForConditionalGeneration
        florence_model_cls = Florence2ForConditionalGeneration
    except ImportError:
        florence_model_cls = AutoModelForCausalLM

    flor_proc = AutoProcessor.from_pretrained("florence-community/Florence-2-base", local_files_only=True, trust_remote_code=True)
    flor_model = florence_model_cls.from_pretrained("florence-community/Florence-2-base", local_files_only=True, trust_remote_code=True).to(device)
    print(f"Florence-2 loaded in {time.time()-t0:.2f}s", flush=True)

    # Brief caption
    inputs = flor_proc(text="<CAPTION>", images=test_img, return_tensors="pt").to(device)
    with torch.no_grad():
        gen_ids = flor_model.generate(**inputs, max_new_tokens=50, num_beams=3)
    res = flor_proc.batch_decode(gen_ids, skip_special_tokens=True)[0]
    print(f"Florence-2 <CAPTION>: {res}", flush=True)

    # Detailed caption
    inputs2 = flor_proc(text="<MORE_DETAILED_CAPTION>", images=test_img, return_tensors="pt").to(device)
    with torch.no_grad():
        gen_ids2 = flor_model.generate(**inputs2, max_new_tokens=80, num_beams=3)
    res2 = flor_proc.batch_decode(gen_ids2, skip_special_tokens=True)[0]
    print(f"Florence-2 <MORE_DETAILED_CAPTION>: {res2}", flush=True)
except Exception as e:
    print(f"Florence-2 Error: {e}", flush=True)
