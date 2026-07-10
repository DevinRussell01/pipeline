import subprocess
import sys
from datetime import datetime

print("===================================")
print("CONDUIT SCAN CENTER")
print("===================================")
print(f"Started: {datetime.now().isoformat(timespec='seconds')}", flush=True)

scripts = [
    "scan_builder_portfolios.py",
    "scan_county_projects.py",
    "scan_gaston_projects.py",
    "scan_mecklenburg_subdivisions.py",
    "scan_union_projects.py",
    "scan_brunswick_projects.py",
    "scan_brunswick_gis.py",
    "land_intelligence.py",
    "scan_locate_signals.py",
    "correlate_locate_signals.py",
    "detect_locate_patterns.py",
    "generate_ai_brief.py",
    "generate_activity_feed.py",
    "generate_ask_conduit.py",
]

passed = []
failed = []

for script in scripts:
    print()
    print(f"Running: {script}", flush=True)
    print("-----------------------------------", flush=True)

    result = subprocess.run(
        [sys.executable, "-u", script],
        text=True
    )

    if result.returncode == 0:
        passed.append(script)
        print(f"PASS: {script}", flush=True)
    else:
        failed.append({
            "script": script,
            "return_code": result.returncode
        })
        print(
            f"FAIL: {script} returned exit code {result.returncode}",
            flush=True
        )

print()
print("===================================")
print("SCAN SUMMARY")
print("===================================")
print(f"Passed: {len(passed)}")
print(f"Failed: {len(failed)}")

for script in passed:
    print(f"  PASS  {script}")

for failure in failed:
    print(
        f"  FAIL  {failure['script']} "
        f"(exit code {failure['return_code']})"
    )

print(f"Finished: {datetime.now().isoformat(timespec='seconds')}")

if failed:
    print()
    print("CONDUIT SCAN COMPLETED WITH ERRORS")
    sys.exit(1)

print()
print("ALL CONDUIT SCANS COMPLETED SUCCESSFULLY")
sys.exit(0)