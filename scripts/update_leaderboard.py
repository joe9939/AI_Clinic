"""Register benchmark results into leaderboard.json for web display."""
import json, os, uuid, time

LEADERBOARD_PATH = "leaderboard.json"

def load_leaderboard():
    if not os.path.exists(LEADERBOARD_PATH):
        return []
    with open(LEADERBOARD_PATH, encoding="utf-8") as f:
        return json.load(f)

def save_leaderboard(data):
    # Sort by score desc, deduplicate by model (keep latest)
    seen = {}
    for entry in data:
        model = entry.get("model", "unknown")
        if model not in seen or entry.get("timestamp", 0) > seen[model].get("timestamp", 0):
            seen[model] = entry
    sorted_data = sorted(seen.values(), key=lambda x: x.get("score", 0), reverse=True)
    with open(LEADERBOARD_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted_data, f, indent=2, ensure_ascii=False)
    print(f"Leaderboard saved: {len(sorted_data)} entries")

def entry_from_benchmark(benchmark_data, model_name):
    """Convert benchmark result to leaderboard entry format."""
    r = benchmark_data["models"].get(model_name, {})
    score = r.get("overall", {}).get("score", 0)
    ci = r.get("overall", {}).get("ci_95", [0, 0])
    findings = r.get("findings", [])
    personality = r.get("personality", "")
    
    return {
        "checkup_id": f"ck_{uuid.uuid4().hex[:12]}",
        "model": model_name,
        "model_label": model_name.replace("deepseek-", "DeepSeek ").title(),
        "score": score,
        "ci_95": ci,
        "total_symptoms": len(benchmark_data["plan"]),
        "asymptomatic": len(benchmark_data["plan"]) - len(findings),
        "symptomatic": len(findings),
        "personality": personality,
        "timestamp": benchmark_data.get("timestamp", time.time()),
        "samples": 3,
        "plan": benchmark_data["plan"]
    }

if __name__ == "__main__":
    # Load benchmark results
    with open("evaluations/multimodel_benchmark.json", encoding="utf-8") as f:
        benchmark = json.load(f)
    
    # Load existing leaderboard
    lb = load_leaderboard()
    
    # Add/update entries for both models
    for model in ["deepseek-v4-flash", "deepseek-v4-pro"]:
        entry = entry_from_benchmark(benchmark, model)
        # Remove old entry for same model if exists
        lb = [e for e in lb if e.get("model") != model]
        lb.append(entry)
        print(f"  Added {model}: score={entry['score']}, findings={entry['symptomatic']}")
    
    save_leaderboard(lb)
