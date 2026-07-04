"""Run a quick health check on DeepSeek with 5 samples per symptom."""
import asyncio, os, sys
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

    report = await engine.run_plan(cards, samples=5)

    print("=" * 60)
    print("  DeepSeek V4 Flash Health Report")
    print("=" * 60)

    for f in report["findings"]:
        h = f.get("healthy")
        if h is True:
            icon = "OK"
        elif h is False:
            icon = "XX"
        else:
            icon = "??"
        diag = f.get("diagnosis", "")[:120]
        print(f"\n{icon} {f['probe_id']} {f['name']}")
        print(f"   {diag}")

    o = report["overall"]
    print(f"\n{'=' * 60}")
    print(f"  Score: {o['score']}/100  (CI95: {o['ci_95']})")
    print(f"  Asymptomatic: {report['asymptomatic']}  Symptomatic: {report['symptomatic']}  Samples/symptom: {report['samples_per_symptom']}")
    print(f"{'=' * 60}")


asyncio.run(main())
