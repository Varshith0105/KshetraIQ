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

questions = [
    "what colors and patterns are visible on the leaf?",
    "describe the spots, blemishes, or lesions on the leaf surface.",
    "what is in the background of the image?",
]

for q in questions:
    text = f"Question: {q} Answer:"
    inp = processor(images=im, text=text, return_tensors="pt")
    with torch.no_grad():
        out = model.generate(**inp, max_new_tokens=60, num_beams=3, repetition_penalty=1.2)
    ans = processor.decode(out[0], skip_special_tokens=True)
    print(f"Q: {q}\nA: {ans}\n")
