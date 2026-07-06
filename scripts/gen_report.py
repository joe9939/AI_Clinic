"""Generate long report from existing checkup results."""
import asyncio, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()
from httpx import AsyncClient
from datetime import datetime
from api.routes import SYMPTOM_CARDS
from ai_clinic.interpreter import build_long_report_prompt, parse_six_dimensions

async def main():
    # Load existing checkup results
    input_path = sys.argv[1] if len(sys.argv) > 1 else "evaluations/deepseek_v4_flash_full.json"
    model = sys.argv[2] if len(sys.argv) > 2 else "deepseek-v4-flash"
    writer_model = sys.argv[3] if len(sys.argv) > 3 else "deepseek-v4-flash"  # LLM that writes the report
    
    with open(input_path, encoding="utf-8") as f:
        raw = json.load(f)
    
    # Build text_report format expected by build_long_report_prompt
    text_report = {
        "model": model,
        "overall": raw["overall"],
        "findings": raw.get("findings", []),
        "asymptomatic": raw.get("asymptomatic", 0),
        "symptomatic": raw.get("symptomatic", 0),
        "total_symptoms": raw.get("total_symptoms", 0),
    }
    
    # Build sample responses from symptom cards
    sample_responses = {}
    for f in text_report["findings"]:
        pid = f["probe_id"]
        card = SYMPTOM_CARDS.get(pid)
        if card:
            sample_responses[pid] = {
                "control": getattr(card, "control_prompt", "") or "",
                "experimental": getattr(card, "experimental_prompt", "") or "",
            }
    
    # Generate prompt and call LLM
    prompt = build_long_report_prompt(text_report, sample_responses)
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    print(f"Generating long report from {input_path}...")
    
    client = AsyncClient(timeout=180.0)
    resp = await client.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": writer_model, "messages": [{"role": "user", "content": prompt}],
              "temperature": 0.7, "max_tokens": 3072},
    )
    report_text = resp.json()["choices"][0]["message"]["content"]
    word_count = len(report_text.split())
    
    # Parse six dimensions
    dimensions = parse_six_dimensions(report_text)
    
    # Save
    output = {
        "model": model,
        "timestamp": datetime.now().isoformat(),
        "word_count": word_count,
        "report": report_text,
        "dimensions": dimensions,
        "score": text_report["overall"]["score"],
        "total_symptoms": text_report["total_symptoms"],
        "asymptomatic": text_report["asymptomatic"],
        "symptomatic": text_report["symptomatic"],
    }
    
    out_path = input_path.replace("_full.json", "_long_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nWord count: {word_count}")
    print(f"Dimensions: {len(dimensions)}")
    for d in dimensions:
        print(f"  {d['emoji']} {d['label']}: {d['persona']}")
    print(f"\nSaved to {out_path}")

asyncio.run(main())
