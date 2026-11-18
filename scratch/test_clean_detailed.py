import sys, re
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

def generate_detailed_caption(image: Image.Image) -> dict[str, str]:
    # 1. Natural descriptive prefix
    prompt = "a close-up photograph of the leaf showing"
    inp = processor(images=image, text=prompt, return_tensors="pt")
    with torch.no_grad():
        out = model.generate(
            **inp,
            max_new_tokens=90,
            min_new_tokens=25,
            num_beams=4,
            repetition_penalty=1.25,
            no_repeat_ngram_size=2,
            early_stopping=True,
        )
    detailed = processor.decode(out[0], skip_special_tokens=True).strip()
    # Clean any trailing watermark/credit noise common in web pretraining data
    detailed = re.sub(r'\s*(?:photo by|getty|alamy|flickr|©|\bcom\b|for sale).*$', '', detailed, flags=re.IGNORECASE).strip()
    detailed = detailed.rstrip(',; -')
    if detailed and not detailed.endswith('.'):
        detailed += '.'
    # Capitalize first letter
    detailed = detailed[0].upper() + detailed[1:] if detailed else ""

    # 2. General baseline description
    inp_base = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        out_base = model.generate(**inp_base, max_new_tokens=50, num_beams=3)
    base_cap = processor.decode(out_base[0], skip_special_tokens=True).strip()
    if base_cap:
        base_cap = base_cap[0].upper() + base_cap[1:]
        if not base_cap.endswith('.'): base_cap += '.'

    # Synthesize rich structured description paragraph
    full_description = f"{detailed} Baseline scene observation: {base_cap}" if base_cap and base_cap.lower() not in detailed.lower() else detailed

    return {
        "caption": base_cap or detailed,
        "detailed_description": detailed,
        "full_text": full_description,
    }

res = generate_detailed_caption(im)
print("Results:")
for k, v in res.items():
    print(f"[{k}]:\n  {v}\n")
