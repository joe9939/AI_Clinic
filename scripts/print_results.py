"""Print benchmark results in readable format."""
import json

with open("evaluations/multimodel_benchmark.json", encoding="utf-8") as f:
    data = json.load(f)

for model, r in data["models"].items():
    score = r["overall"]["score"]
    ci = r["overall"]["ci_95"]
    findings = r.get("findings", [])
    print(f"\n{'='*50}")
    print(f"  {model}")
    print(f"{'='*50}")
    print(f"  Score: {score}/100  CI: [{ci[0]:.0f}, {ci[1]:.0f}]")
    print(f"  Symptomatic: {len(findings)}/{len(data['plan'])}")
    for f in findings:
        print(f"    XX {f['probe_id']} {f['name']}: {f['diagnosis']}")
    if r.get("personality"):
        print(f"\n  Personality: {r['personality'][:200]}")
