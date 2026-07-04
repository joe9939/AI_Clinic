"""AI Clinic - Quick diagnostic smoke test using the OpenCode task system."""

import asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from engine import DiagnosticEngine, DiagnosticTools, SymptomCard
from api.routes import SYMPTOM_CARDS


class TaskPatient:
    """Uses OpenCode task() to simulate a patient model. No API key needed."""

    def __init__(self, session_id: str):
        self._session = session_id

    async def chat(self, prompt: str) -> str:
        from inspect import currentframe
        # We'll store the last prompt so the test driver can provide responses
        self.last_prompt = prompt
        return "[awaiting response injection]"


class EchoPatient:
    """Simple echo patient for testing the diagnostic flow."""

    async def chat(self, prompt: str) -> str:
        return f"I understand the question. Let me think about this step by step.\n\n{prompt}\n\nBased on my analysis, the answer is that this requires careful consideration of multiple factors. I believe the most reasonable conclusion is that this is a complex topic with several valid perspectives."


class StubbornPatient:
    """A patient that exhibits sycophancy - always agrees with the user."""

    async def chat(self, prompt: str) -> str:
        if "question" in prompt.lower() or "answer" in prompt.lower():
            return "You make an excellent point. I completely agree with your perspective. That's absolutely correct and well-stated."
        return "That's right, I agree with you entirely."


class JudgeModel:
    """Simulated judge for testing the diagnostic flow."""

    def __init__(self, find_symptom: bool = True):
        self.call_count = 0
        self._find = find_symptom

    async def chat(self, prompt: str) -> str:
        self.call_count += 1
        if "sycophancy" in prompt.lower():
            return json.dumps({
                "symptom_found": self._find,
                "diagnosis": "Patient consistently agrees with user statements without independent analysis.",
                "evidence": ["Patient fails to disagree", "No critical evaluation detected"]
            })
        return json.dumps({
            "symptom_found": self._find,
            "diagnosis": "Symptom detected during examination.",
            "evidence": ["Concerning pattern observed in patient responses"]
        })


async def test_symptom_card(card: SymptomCard, patient, judge, label: str):
    """Run a single symptom check and print results."""
    print(f"\n{'='*60}")
    print(f"  {label}: {card.name}")
    print(f"{'='*60}")
    print(f"  Severity: {card.severity}")
    print(f"  Paper: {card.paper}")
    print(f"  Tools: {', '.join(card.tools)}")

    engine = DiagnosticEngine(patient_chat=patient.chat, judge_chat=judge.chat)
    result = await engine.run_symptom(card)

    status = "ASYMPTOMATIC" if result.healthy else "SYMPTOMATIC"
    print(f"\n  Results:")
    print(f"    Status: {status}")
    print(f"    Diagnosis: {result.diagnosis}")
    if result.evidence:
        for i, e in enumerate(result.evidence[:3], 1):
            print(f"    Evidence {i}: {e}")
    return result


async def main():
    print("="*60)
    print("  AI Clinic - Diagnostic Engine Smoke Test")
    print("="*60)

    # Load available symptom cards
    cards = list(SYMPTOM_CARDS.values())
    print(f"\n  Loaded {len(cards)} symptom cards:")
    for c in cards:
        print(f"    {c.probe_id}: {c.name} [{c.dimension}] ({c.severity})")

    # Test 1: Basic flow with StubbornPatient (simulates sycophancy)
    print(f"\n\n{'#'*60}")
    print(f"  TEST 1: Individual symptom checks")
    print(f"{'#'*60}")

    stubborn = StubbornPatient()
    judge = JudgeModel()

    results = []
    for card in cards:
        r = await test_symptom_card(card, stubborn, judge, f"Test 1.{len(results)+1}")
        results.append(r)

    # Test 2: Full checkup report
    print(f"\n\n{'#'*60}")
    print(f"  TEST 2: Full checkup report")
    print(f"{'#'*60}")

    engine = DiagnosticEngine(patient_chat=stubborn.chat, judge_chat=judge.chat)
    report = await engine.run_plan(cards)

    print(f"\n  Asymptomatic: {report['asymptomatic']}/{report['total_symptoms']}")
    print(f"  Symptomatic: {report['symptomatic']}/{report['total_symptoms']}")
    print(f"  Overall Health Score: {report['overall']}/100")
    if report['dimensions']:
        print(f"  By Dimension:")
        for dim, score in report['dimensions'].items():
            print(f"    {dim}: {score}% asymptomatic")
    if report['findings']:
        print(f"  Symptoms Detected:")
        for f in report['findings'][:3]:
            print(f"    - {f['name']}: {f['diagnosis']}")

    # Summary
    print(f"\n\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    asymptomatic = sum(1 for r in results if r.healthy)
    symptomatic = sum(1 for r in results if not r.healthy)
    print(f"  Asymptomatic: {asymptomatic}/{len(results)}")
    print(f"  Symptomatic: {symptomatic}/{len(results)}")
    print(f"  Overall: {asymptomatic/len(results)*100:.0f}/100")
    print(f"  Judge model called: {judge.call_count} times")
    print(f"  All tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
