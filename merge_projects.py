import json

all_projects = []

for filename in [
    "projects.json",
    "union_projects.json",
    "gaston_projects.json"
]:
    with open(filename, "r") as file:
        data = json.load(file)

        if isinstance(data, list):
            all_projects.extend(data)
        else:
            all_projects.append(data)

with open("projects.json", "w") as file:
    json.dump(all_projects, file, indent=4)

print("Merged projects saved to projects.json")
print("Total projects:", len(all_projects))