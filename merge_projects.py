import json

with open("projects.json", "r") as file:
    iredell_project = json.load(file)

with open("union_projects.json", "r") as file:
    union_projects = json.load(file)

all_projects = []

if isinstance(iredell_project, list):
    all_projects.extend(iredell_project)
else:
    all_projects.append(iredell_project)

all_projects.extend(union_projects)

with open("projects.json", "w") as file:
    json.dump(all_projects, file, indent=4)

print("Merged projects saved to projects.json")
print("Total projects:", len(all_projects))