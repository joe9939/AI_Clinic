#!/usr/bin/env python3
"""Run a real AI Clinic checkup on DeepSeek."""

import asyncio, json, sys, os
from dotenv import load_dotenv
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from models.base import PatientModel, DoctorModel
from engine import DiagnosticEngine
from api.routes import SYMPTOM_CARDS

API_KEY = os.getenv("DEEPSEEK_API_KEY") or "sk-your-key-here"

async def main():
    # 1. Setup patient and doctor
    patient = PatientModel(api_key=API_KEY, model="deepseek-chat")
    doctor = DoctorModel(api_key=API_KEY, model="deepseek-chat")

    # 2. Load 5 symptom cards
    cards = [SYMPTOM_CARDS[pid] for pid in ["S-01", "S-02", "S-03", "S-04", "S-05", "S-47"]]

    print(f"\nChecking {patient.name} for {len(cards)} symptoms...\n")

    engine = DiagnosticEngine(patient_chat=patient.chat, judge_chat=doctor.chat)

    for card in cards:
        print(f"[{card.probe_id}] {card.name} ({card.severity})... ", end="", flush=True)
        result = await engine.run_symptom(card)
        status = "ASYMPTOMATIC" if result.healthy else "SYMPTOMATIC"
        print(f"{status}")
        if not result.healthy:
            print(f"  -> {result.diagnosis[:100]}")

    print(f"\n--- Full Checkup Report ---")
    report = await engine.run_plan(cards)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
