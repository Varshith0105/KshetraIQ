import re

with open("frontend/src/app/page.tsx", "r", encoding="utf-8") as f:
    content = f.read()

print("File size:", len(content), "characters, lines:", len(content.splitlines()))

# Find view declarations, states, tabs, endpoints called
views = re.findall(r'function\s+([A-Z]\w+View)', content)
print("Views found:", set(views))

tabs = re.findall(r'activeTab\s*===\s*["\']([^"\']+)["\']', content)
print("Active tabs found:", set(tabs))

fetches = re.findall(r'fetch\([`"\']([^`"\']*)', content)
print("Endpoints called via fetch:", set(fetches[:20]))

# Search for any inputs or components declared inside Home
home_start = content.find("export default function Home")
if home_start != -1:
    home_code = content[home_start:]
    inner_comps = re.findall(r'function\s+([A-Z]\w+)\s*\(', home_code)
    print("Inner components in Home():", inner_comps)
