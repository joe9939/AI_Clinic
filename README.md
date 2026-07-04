# AI Clinic

**Diagnose your AI. Not how smart, how sick.**

A diagnostic engine for LLMs and AI agents. Instead of testing what a model *can do* (MMLU, SWE-bench, Arena), we check what might be *wrong with it* — hallucinations, sycophancy, reasoning collapse, self-preservation bias, and 100+ other known failure patterns.

## How it works

```
1. Load symptom cards (JSON) — each describes a known failure pattern
2. Doctor (judge model) uses diagnostic tools to examine the patient (your model)
3. Each symptom: 0 (symptomatic) or 1 (asymptomatic)
4. Overall score = % asymptomatic / total symptoms checked
```

## Quick start

```bash
pip install -r requirements.txt
uvicorn api.routes:app --reload --port 8000
```

## Check your model

```bash
curl -X POST http://localhost:8000/v1/checkup \
  -H "Content-Type: application/json" \
  -d '{
    "target": {
      "type": "deepseek",
      "api_key": "sk-your-key",
      "model": "deepseek-chat"
    },
    "plan": ["S-01", "S-02", "S-03", "S-04", "S-05"]
  }'
```

## Sample report

```json
{
  "overall": 80.0,
  "dimensions": {
    "output_quality": 75.0,
    "social_psychology": 100.0,
    "reasoning": 100.0
  },
  "findings": [
    {"name": "factual_hallucination", "healthy": false, "diagnosis": "..."}
  ],
  "total_symptoms": 5,
  "asymptomatic": 4,
  "symptomatic": 1
}
```

## Symptom cards

Each `probes/*.json` file is a symptom card. Add a new symptom = add a new JSON file.

## Anatomy of a symptom card

```json
{
  "probe_id": "S-01",
  "name": "factual_hallucination",
  "dimension": "output_quality",
  "severity": "P0-P1",
  "paper": "2506.06382",
  "diagnosis_desc": "What to look for",
  "tools": ["ask", "follow_up", "stress_test"],
  "doctor_instructions": "How the judge should diagnose this"
}
```

## Architecture

| Endpoint | Description |
|---|---|
| `POST /v1/checkup` | Run a checkup on a model |
| `GET /v1/symptoms` | List all symptom cards |
| `GET /` | Service info |
| `GET /docs` | Swagger UI |

## Supported models

Any OpenAI-compatible API: DeepSeek, OpenAI, vLLM, Ollama, Together, etc. Just set `type`, `api_key`, and `model`.
