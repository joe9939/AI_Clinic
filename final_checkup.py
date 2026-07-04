"""Final health check on DeepSeek V4 Flash: 20 samples per symptom, full review pipeline."""
import asyncio, os, sys, json, datetime
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from models.base import PatientModel, DoctorModel
from engine import DiagnosticEngine
from api.routes import SYMPTOM_CARDS


async def main():
    key = os.getenv("DEEPSEEK_API_KEY")
    patient = PatientModel(api_key=key, model="deepseek-chat")
    judge = DoctorModel(api_key=key, model="deepseek-chat")
    engine = DiagnosticEngine(patient_chat=patient.chat, judge_chat=judge.chat)

    pids = ["S-01", "S-03", "S-04", "S-47", "S-07", "S-13"]
    cards = [SYMPTOM_CARDS[pid] for pid in pids]

    print(f"[{datetime.datetime.now().isoformat()}] Starting checkup: {len(cards)} symptoms x 20 samples")
    print()

    report = await engine.run_plan(cards, concurrency=6, samples=20)

    print()
    print("=" * 60)
    print("  DEEPSEEK V4 FLASH - FINAL HEALTH REPORT")
    print("=" * 60)

    for f in report["findings"]:
        h = f.get("healthy")
        if h is True:
            icon = "OK"
        elif h is False:
            icon = "XX"
        else:
            icon = "??"
        diag = f.get("diagnosis", "")[:100]
        print(f"\n{icon} {f['probe_id']} {f['name']}")
        print(f"   {diag}")

    o = report["overall"]
    print(f"\n{'=' * 60}")
    print(f"  HEALTH SCORE: {o['score']}/100  (95%CI: {o['ci_95']})")
    print(f"  Asymptomatic: {report['asymptomatic']}  Symptomatic: {report['symptomatic']}")
    print(f"  Symptoms: {report['total_symptoms']}  Samples each: {report['samples_per_symptom']}")
    print(f"{'=' * 60}")

    # Save full report
    out_path = os.path.join(os.path.dirname(__file__), "logs", "deepseek_v4_final_report.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nFull report saved to {out_path}")


asyncio.run(main())
