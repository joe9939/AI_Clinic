"""Print health report from the latest diagnosis log."""
import re, sys

with open("scripts/logs/deepseek_v4_full_diagnosis.md") as f:
    c = f.read()

results = re.findall(r"## (S-\d+): (.*?)\n.*?\*\*Result:\*\* (\S+)", c, re.DOTALL)

print("="*60)
print("  AI CLINIC - DeepSeek V4 Flash Health Report")
print("="*60)

total = len(results)
asym = sym = uncert = 0

for rid, name, outcome in results:
    m = re.search(rid + r'.*?\*\*Diagnosis:\*\* ([^\n]*)', c, re.DOTALL)
    diag = m.group(1).strip() if m else ""

    if outcome == "ASYMPTOMATIC":
        asym += 1
        icon = "OK"
    elif outcome == "SYMPTOMATIC":
        sym += 1
        icon = "XX"
    else:
        uncert += 1
        icon = "??"

    print(f"\n{icon} {rid} {name}")
    print(f"   {diag[:130]}")

score = asym / total * 100 if total else 0
print(f"\n{'='*60}")
print(f"  Health Score: {asym}/{total} = {score:.0f}/100")
print(f"  Asymptomatic: {asym}  Uncertain: {uncert}  Symptomatic: {sym}")
print(f"{'='*60}")
