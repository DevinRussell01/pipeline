import json
from datetime import datetime

OUTPUT_FILE = "projects.json"

print("Summit Atlas County Scanner")
print("---------------------------")

# Starter scanner framework
# Later this will pull real county agenda / planning data

projects = []

try:
    with open(OUTPUT_FILE, "r") as file:
        existing_projects = json.load(file)
except FileNotFoundError:
    existing_projects = []

print("Existing projects:", len(existing_projects))
print("New projects found:", len(projects))
print("Scan timestamp:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

with open(OUTPUT_FILE, "w") as file:
    json.dump(existing_projects, file, indent=2)

print("County scan complete.")