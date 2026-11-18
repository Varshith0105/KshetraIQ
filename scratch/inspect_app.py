with open('frontend/src/app/plant-intelligence/page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

print('Length of plant-intelligence/page.tsx:', len(text))
print(text[:500])
