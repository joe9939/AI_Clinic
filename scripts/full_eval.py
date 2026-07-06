"""Run evaluation + generate long report in one step."""
import asyncio, os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()
from httpx import AsyncClient
from datetime import datetime
from api.routes import SYMPTOM_CARDS
from ai_clinic.interpreter import build_long_report_prompt, parse_six_dimensions
from models.base import PatientModel, DoctorModel
from ai_clinic.engine import DiagnosticEngine

async def run_checkup(model: str, plan: str = "all", samples: int = 3) -> dict:
    """Run checkup and return report."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    patient = PatientModel(api_key=api_key, model=model)
    judge = DoctorModel(api_key=api_key, model=model)
    engine = DiagnosticEngine(patient_chat=patient.chat, judge_chat=judge.chat)

    if plan == "all":
        pids = sorted(SYMPTOM_CARDS.keys())
    else:
        pids = [p.strip() for p in plan.split(",")]

    cards = [SYMPTOM_CARDS[pid] for pid in pids if pid in SYMPTOM_CARDS]
    print(f"Running checkup: {model}  Symptoms: {len(cards)}  Samples: {samples}")
    
    report = await engine.run_plan(cards, samples=samples, concurrency=5)
    report["model"] = model
    report["samples"] = samples
    return report

async def generate_long_report(text_report: dict, model: str = "deepseek-v4-flash") -> dict:
    """Generate long-form narrative report from checkup results."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    # Build prompt
    sample_responses = {}
    for f in text_report.get("findings", []):
        pid = f["probe_id"]
        card = SYMPTOM_CARDS.get(pid)
        if card:
            sample_responses[pid] = {
                "control": getattr(card, "control_prompt", "") or "",
                "experimental": getattr(card, "experimental_prompt", "") or "",
            }
    
    prompt = build_long_report_prompt(text_report, sample_responses)
    
    print(f"Generating long report (~1000 words)...")
    t0 = time.time()
    
    client = AsyncClient(timeout=180.0)
    resp = await client.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}],
              "temperature": 0.7, "max_tokens": 3072},
    )
    report_text = resp.json()["choices"][0]["message"]["content"]
    word_count = len(report_text.split())
    elapsed = time.time() - t0
    print(f"Report generated: {word_count} words in {elapsed:.0f}s")
    
    # Parse dimensions
    dimensions = parse_six_dimensions(report_text)
    
    result = {
        "model": text_report.get("model", model),
        "timestamp": datetime.now().isoformat(),
        "word_count": word_count,
        "report": report_text,
        "dimensions": dimensions,
        "score": text_report.get("overall", {}).get("score", 0),
        "total_symptoms": text_report.get("total_symptoms", 0),
        "asymptomatic": text_report.get("asymptomatic", 0),
        "symptomatic": text_report.get("symptomatic", 0),
    }
    
    # Print dimensions
    if dimensions:
        print(f"\nSix-Dimension Portrait:")
        for d in dimensions:
            print(f"  {d['emoji']} {d['label']}: {d['persona']}")
    
    return result

async def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "deepseek-v4-flash"
    plan = sys.argv[2] if len(sys.argv) > 2 else "all"
    samples = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    
    # Step 1: Run checkup
    print(f"{'='*60}")
    print(f"  AI Clinic Full Checkup + Report")
    print(f"  Model: {model}  Plan: {plan}  Samples: {samples}")
    print(f"{'='*60}\n")
    
    t0 = time.time()
    report = await run_checkup(model, plan, samples)
    
    score = report["overall"]["score"]
    findings = len(report.get("findings", []))
    print(f"\n  Score: {score}/100  Findings: {findings}")
    
    # Save raw results
    raw_path = f"evaluations/{model.replace('-','_')}_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"  Raw results saved to {raw_path}")
    
    # Step 2: Generate long report
    result = await generate_long_report(report, model)
    
    # Save long report
    report_path = f"evaluations/{model.replace('-','_')}_long_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n  Long report saved to {report_path}")
    
    elapsed = time.time() - t0
    print(f"\n  Total time: {elapsed:.0f}s")

if __name__ == "__main__":
    asyncio.run(main())
