import sys
sys.path.insert(0, 'backend')
from pathlib import Path
from PIL import Image
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration

test_img = None
for p in Path('.uploads').rglob('*'):
    if p.suffix.lower() in ['.jpg', '.jpeg', '.png'] and 'original' in p.name:
        test_img = p
        break

im = Image.open(test_img).convert("RGB")
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base", local_files_only=True)
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base", local_files_only=True)

# Test various prefix prompts
prompts = [
    "a close-up of a leaf showing",
    "a photo of a plant leaf with",
    "a close up photograph of the crop leaf displaying",
    "the visible leaf blade features",
    "the leaf surface shows several",
]

for p in prompts:
    inp = processor(images=im, text=p, return_tensors="pt")
    with torch.no_grad():
        out = model.generate(
            **inp,
            max_new_tokens=80,
            min_new_tokens=25,
            num_beams=4,
            no_repeat_ngram_size=2,
            repetition_penalty=1.2,
            early_stopping=True,
        )
    text = processor.decode(out[0], skip_special_tokens=True)
    print(f"--- Prefix: '{p}' ---")
    print(text)
    print()
