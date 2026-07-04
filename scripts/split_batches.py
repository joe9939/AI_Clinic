"""Split symptom cards into batches for parallel processing."""
import json, os

d = "probes"
cards = sorted([f for f in os.listdir(d) if f.endswith(".json")])
need = []
for f in cards:
    c = json.load(open(os.path.join(d, f)))
    if not (c.get("control_prompt") and c.get("experimental_prompt")):
        need.append(c["probe_id"])

print(f"Symptoms needing prompts: {len(need)}")
n = len(need)
batch_size = n // 10 + 1
for i in range(10):
    batch = need[i * batch_size : (i + 1) * batch_size]
    if batch:
        print(
            f"Batch {i+1}: {batch[0]} to {batch[-1]} ({len(batch)} symptoms)"
        )
