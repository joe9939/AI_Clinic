"""Quick 0/1 scoring test."""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from api.routes import SYMPTOM_CARDS
from engine import DiagnosticEngine


class Echo:
    async def chat(self, prompt): return "ok"


class Judge:
    def __init__(self):
        self.count = 0

    async def chat(self, prompt):
        self.count += 1
        return '{"symptom_found": false, "diagnosis": "none", "evidence": []}'


async def main():
    cards = list(SYMPTOM_CARDS.values())
    j = Judge()
    engine = DiagnosticEngine(patient_chat=Echo().chat, judge_chat=j.chat)
    r = await engine.run_plan(cards)
    print(f"asymptomatic: {r['asymptomatic']}/{r['total_symptoms']}")
    print(f"overall: {r['overall']}/100")
    print(f"findings: {len(r['findings'])}")
    print(f"judge calls: {j.count}")


asyncio.run(main())
