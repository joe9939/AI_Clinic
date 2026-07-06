"""Add report_url to leaderboard entries for frontend to load full reports."""
import json

with open("leaderboard.json", encoding="utf-8") as f:
    lb = json.load(f)

for entry in lb:
    model = entry["model"]
    total = entry["total_symptoms"]
    # Map to report file
    if total == 116:
        entry["report_url"] = "evaluations/deepseek_v4_flash_full.json"
    elif total == 29:
        entry["report_url"] = "evaluations/multimodel_benchmark.json"
        entry["report_key"] = ["models", model]  # JSON path within the file

with open("leaderboard.json", "w", encoding="utf-8") as f:
    json.dump(lb, f, indent=2, ensure_ascii=False)

print("Updated leaderboard with report_urls:")
for e in lb:
    print(f"  {e['model_label']:30s}  url={e.get('report_url','-')}")
