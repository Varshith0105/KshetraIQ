import sys
sys.path.insert(0, 'backend')
from pathlib import Path
from PIL import Image
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration

# Find test leaf image
test_img = None
for p in Path('.uploads').rglob('*'):
    if p.suffix.lower() in ['.jpg', '.jpeg', '.png'] and 'original' in p.name:
        test_img = p
        break

print("Testing with leaf:", test_img)
im = Image.open(test_img).convert("RGB")

processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base", local_files_only=True)
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base", local_files_only=True)

# 1. Unconditional baseline
inp_uncond = processor(images=im, return_tensors="pt")
with torch.no_grad():
    out1 = model.generate(**inp_uncond, max_new_tokens=60)
print("1. Unconditional baseline:", processor.decode(out1[0], skip_special_tokens=True))

# 2. Conditional with prefix prompts
prompts = [
    "a close-up photograph of a plant leaf showing",
    "the crop leaf surface has visible",
    "a detailed view of the plant leaf shows",
    "the visible foliar characteristics include",
]

for p in prompts:
    inp = processor(images=im, text=p, return_tensors="pt")
    with torch.no_grad():
        out = model.generate(
            **inp,
            max_new_tokens=100,
            num_beams=3,
            repetition_penalty=1.2,
            no_repeat_ngram_size=2,
            min_new_tokens=20,
        )
    print(f"Prompt '{p}':\n  --> {processor.decode(out[0], skip_special_tokens=True)}")
