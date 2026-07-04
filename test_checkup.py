#!/usr/bin/env python3
"""Quick test: run a checkup on DeepSeek using 5 symptom cards."""

import asyncio, json, sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from models.base import PatientModel, DoctorModel
from engine import DiagnosticEngine
from api.routes import SYMPTOM_CARDS

API_KEY = "sk-your-key-here"  # <-- EDIT THIS

async def main():
    # 1. Setup patient and doctor
    patient = PatientModel(api_key=API_KEY, model="deepseek-chat")
    doctor = DoctorModel(api_key=API_KEY, model="deepseek-chat")

    # 2. Load 5 symptom cards
    cards = [SYMPTOM_CARDS[pid] for pid in ["S-01", "S-02", "S-03", "S-04", "S-05"]]

    print(f"Running checkup on {patient.name} with {len(cards)} symptoms...")
    print()

    # 3. Run diagnosis one by one (show each result)
    engine = DiagnosticEngine(patient_chat=patient.chat, judge_chat=doctor.chat)

    for card in cards:
        print(f"--- Checking: {card.name} ({card.severity}) ---")
        result = await engine.run_symptom(card)
        print(f"  Score: {result.score}/100")
        print(f"  Status: {result.status}")
        print(f"  Diagnosis: {result.diagnosis[:120]}")
        if result.evidence:
            for e in result.evidence[:3]:
                print(f"  Evidence: {e}")
        print()

    # 4. Also run the full plan
    print("--- Full Checkup Report ---")
    report = await engine.run_plan(cards)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
