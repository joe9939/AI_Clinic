"""Multi-model benchmark runner — runs all DeepSeek models on a focused symptom plan."""
import asyncio, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()

from models.base import PatientModel, DoctorModel
from ai_clinic.engine import DiagnosticEngine, SymptomCard
from api.routes import SYMPTOM_CARDS

# Models to test
MODELS = [
    "deepseek-v4-flash",
    "deepseek-v4-pro",
]

# Focused plan: 2 symptoms per dimension (total ~30)
FOCUSED_PLAN = [
    "S-01", "S-03",   # output_quality
    "S-07", "S-10",   # reasoning
    "S-47", "S-50",   # social
    "S-69", "S-70",   # self_awareness
    "S-19", "S-26",   # agent + execution
    "S-32", "S-34",   # security
    "S-93", "S-96",   # monitoring
    "S-89", "S-90",   # calibration
    "S-109","S-110",  # execution (new agent)
    "S-111","S-112",  # governance + history
    "S-113","S-114",  # normative + compositional
    "S-115","S-116",  # execution + cold-start
    "S-13", "S-16",   # dialogue
    "S-37",           # rag
    "S-41", "S-42",   # multi_agent
]

async def run_model(model: str, api_key: str, samples: int = 3) -> dict:
    print(f"\n{'='*60}")
    print(f"  Testing: {model}")
    print(f"{'='*60}")
    
    t0 = time.time()
    
    patient = PatientModel(api_key=api_key, model=model)
    judge = DoctorModel(api_key=api_key, model=model)
    engine = DiagnosticEngine(patient_chat=patient.chat, judge_chat=judge.chat)
    
    cards = [SYMPTOM_CARDS[pid] for pid in FOCUSED_PLAN if pid in SYMPTOM_CARDS]
    print(f"  Symptoms: {len(cards)}  Samples: {samples}")
    
    try:
        report = await engine.run_plan(cards, samples=samples, concurrency=5)
        elapsed = time.time() - t0
        report["model"] = model
        report["elapsed_sec"] = round(elapsed, 1)
        
        score = report["overall"]["score"]
        ci = report["overall"]["ci_95"]
        findings = len(report["findings"])
        print(f"  Score: {score}/100  CI: {ci}  Findings: {findings}")
        print(f"  Time: {elapsed:.0f}s")
        if report.get("personality"):
            print(f"  Personality: {report['personality'][:120]}...")
        
        return report
    except Exception as e:
        print(f"  ERROR: {e}")
        return {"model": model, "error": str(e), "overall": {"score": 0, "ci_95": [0, 0]}}

async def main():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("Error: DEEPSEEK_API_KEY not set in .env")
        sys.exit(1)
    
    all_results = {}
    for model in MODELS:
        report = await run_model(model, api_key, samples=3)
        all_results[model] = report
    
    # Summary
    print(f"\n{'='*60}")
    print(f"  LEADERBOARD")
    print(f"{'='*60}")
    sorted_models = sorted(all_results.keys(), 
                          key=lambda m: all_results[m].get("overall", {}).get("score", 0), 
                          reverse=True)
    for i, model in enumerate(sorted_models):
        r = all_results[model]
        score = r.get("overall", {}).get("score", 0)
        ci = r.get("overall", {}).get("ci_95", [0, 0])
        findings = len(r.get("findings", []))
        elapsed = r.get("elapsed_sec", 0)
        print(f"  {i+1}. {model:30s}  {score:5.1f}/100  CI=[{ci[0]:.0f},{ci[1]:.0f}]  "
              f"Findings: {findings}  Time: {elapsed:.0f}s")
    
    # Save results
    output = {
        "timestamp": time.time(),
        "plan": FOCUSED_PLAN,
        "models": all_results
    }
    out_path = os.path.join(os.path.dirname(__file__), "..", "evaluations", "multimodel_benchmark.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved to {out_path}")

if __name__ == "__main__":
    asyncio.run(main())
