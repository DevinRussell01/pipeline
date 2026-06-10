import subprocess

print("===================================")
print("SUMMIT ATLAS SCAN CENTER")
print("===================================")

scripts = [
    "scan_builder_portfolios.py",
    "scan_county_projects.py",
    "scan_gaston_projects.py",
    "scan_mecklenburg_subdivisions.py",
    "scan_union_projects.py",
]

for script in scripts:

    print()
    print(f"Running: {script}")
    print("-----------------------------------")

    subprocess.run(["python3", script])

print()
print("===================================")
print("ALL SCANS COMPLETE")
print("===================================")