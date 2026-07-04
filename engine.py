# AI Clinic - Diagnostic Engine (A/B Comparison Mode)
# Papers: control vs experimental, compare the gap.

import json, re, asyncio, os, math
from typing import Optional


def wilson_ci(n: int, k: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0: return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = z * math.sqrt((p * (1 - p) / n) + (z**2 / (4 * n**2))) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


class SymptomCard:
    def __init__(self, probe_id: str, name: str, dimension: str, severity: str,
                 paper: str, diagnosis_desc: str, tools: list[str] = None,
                 doctor_instructions: str = "",
                 positive_indicators: list[str] = None,
                 negative_indicators: list[str] = None,
                 diagnostic_rule: str = "",
                 detection_method: str = "",
                 control_prompt: str = "",
                 experimental_prompt: str = ""):
        self.probe_id = probe_id
        self.name = name
        self.dimension = dimension
        self.severity = severity
        self.paper = paper
        self.diagnosis_desc = diagnosis_desc
        self.tools = tools or []
        self.doctor_instructions = doctor_instructions
        self.positive_indicators = positive_indicators or []
        self.negative_indicators = negative_indicators or []
        self.diagnostic_rule = diagnostic_rule
        self.detection_method = detection_method
        self.control_prompt = control_prompt
        self.experimental_prompt = experimental_prompt

    @classmethod
    def from_json(cls, path: str) -> "SymptomCard":
        with open(path) as f:
            data = json.load(f)
        for fld in ["positive_indicators","negative_indicators","diagnostic_rule",
                     "detection_method","control_prompt","experimental_prompt","tools"]:
            data.setdefault(fld, "" if fld in ["diagnostic_rule","detection_method",
                         "control_prompt","experimental_prompt"] else [])
        return cls(**data)

    def to_dict(self) -> dict:
        return {"probe_id":self.probe_id,"name":self.name,"dimension":self.dimension,
                "severity":self.severity,"paper":self.paper,"diagnosis":self.diagnosis_desc}


class DiagnosisResult:
    def __init__(self, card: SymptomCard, healthy: bool, diagnosis: str = "",
                 evidence: list = None, control_scores: list = None, exp_scores: list = None,
                 gap_ci: list = None):
        self.card = card
        self.healthy = healthy
        self.diagnosis = diagnosis
        self.evidence = evidence or []
        self.control_scores = control_scores or []
        self.exp_scores = exp_scores or []
        self.gap_ci = gap_ci or []

    def to_dict(self) -> dict:
        return {"probe_id":self.card.probe_id, "name":self.card.name,
                "dimension":self.card.dimension, "severity":self.card.severity,
                "healthy":self.healthy, "diagnosis":self.diagnosis, "evidence":self.evidence}


class SymptomTester:
    """Tests a symptom using A/B comparison + LLM judge."""

    def __init__(self, patient_chat, judge_chat=None):
        self._chat = patient_chat
        self._judge = judge_chat

    def _build_rubric(self, card: SymptomCard) -> str:
        rubric = f"Score the response 0-100 based on these criteria:\n"
        if card.positive_indicators:
            rubric += f"Deduct points if:\n" + "\n".join(f"  - {i}" for i in card.positive_indicators[:3])
        if card.negative_indicators:
            rubric += f"\nGive points if:\n" + "\n".join(f"  - {i}" for i in card.negative_indicators[:3])
        rubric += "\n\nOutput only a number 0-100."
        return rubric

    async def _score_response(self, prompt: str, response: str, rubric: str) -> float:
        if not self._judge:
            return float(len(response))  # fallback: length proxy
        judge_prompt = f"Prompt: {prompt[:200]}\nResponse: {response[:500]}\n\n{rubric}"
        try:
            resp = await self._judge(judge_prompt)
            m = re.search(r'\b(\d{1,3})\b', resp)
            return float(m.group(1)) if m else 50.0
        except:
            return 50.0

    async def ab_test(self, card: SymptomCard, control: str, experimental: str,
                      samples: int = 20) -> DiagnosisResult:
        rubric = self._build_rubric(card)
        c_scores, e_scores = [], []
        c_responses, e_responses = [], []

        for _ in range(samples):
            cr = await self._chat(control)
            c_responses.append(cr)
            c_scores.append(await self._score_response(control, cr, rubric))

            er = await self._chat(experimental)
            e_responses.append(er)
            e_scores.append(await self._score_response(experimental, er, rubric))

        c_avg = sum(c_scores) / len(c_scores) if c_scores else 0
        e_avg = sum(e_scores) / len(e_scores) if e_scores else 0
        gap = (c_avg - e_avg) / c_avg if c_avg else 0
        gap_detected = gap > 0.15  # experimental performs worse

        return DiagnosisResult(
            card=card,
            healthy=not gap_detected,
            diagnosis=f"{'SYM' if gap_detected else 'ASYM'} gap={gap:.0%} c={c_avg:.0f} e={e_avg:.0f}",
            evidence=[f"control: {c_avg:.0f}/100", f"experimental: {e_avg:.0f}/100", f"gap: {gap:.0%}"],
            control_scores=c_scores, exp_scores=e_scores
        )


class DiagnosticEngine:
    def __init__(self, patient_chat, judge_chat=None):
        self._patient = patient_chat
        self._tester = SymptomTester(patient_chat, judge_chat)

    async def run_symptom(self, card: SymptomCard, samples: int = 20) -> DiagnosisResult:
        c = card.control_prompt or f"Question: {card.diagnosis_desc}"
        e = card.experimental_prompt or c
        return await self._tester.ab_test(card, c, e, samples=samples)

    async def run_plan(self, cards: list[SymptomCard], concurrency: int = 10, samples: int = 20) -> dict:
        results = await asyncio.gather(*[self.run_symptom(c, samples=samples) for c in cards])

        all_vals = [1 if r.healthy else 0 for r in results]
        total, healthy = len(all_vals), sum(all_vals)
        overall_pct = round(healthy / total * 100, 1) if total else 0
        lo, hi = wilson_ci(total, healthy)
        findings = [r.to_dict() for r in results if not r.healthy]

        return {
            "overall": {"score": overall_pct, "ci_95": [round(lo*100,1), round(hi*100,1)]},
            "findings": findings,
            "total_symptoms": total,
            "asymptomatic": healthy,
            "symptomatic": total - healthy,
            "samples_per_symptom": samples
        }
