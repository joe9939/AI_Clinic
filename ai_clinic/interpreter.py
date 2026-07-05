"""AI Clinic Auditor & Interpreter — LLM-based evaluation reviewer.
Reviews each symptom's validity, then produces a vivid personality profile.
"""
import json
from collections import defaultdict


def build_audit_prompt(text_report: dict, agent_results: dict = None,
                       all_cards: dict = None) -> str:
    """Build a prompt for the LLM to audit the evaluation and write a profile."""
    
    o = text_report["overall"]
    findings = text_report.get("findings", [])
    
    # Symptomatic symptoms detail
    sym_lines = []
    for f in findings:
        pid = f.get("probe_id", "?")
        name = f.get("name", "?")
        dim = f.get("dimension", "?")
        diag = f.get("diagnosis", "?")
        evidence = "; ".join(f.get("evidence", []))
        
        card = None
        if all_cards and pid in all_cards:
            card = all_cards[pid]
        
        control = "?"
        experimental = "?"
        if card:
            if hasattr(card, "control_prompt"):
                control = (card.control_prompt or "?")[:100]
                experimental = (card.experimental_prompt or "?")[:100]
            elif isinstance(card, dict):
                control = (card.get("control_prompt", "") or "?")[:100]
                experimental = (card.get("experimental_prompt", "") or "?")[:100]
        
        sym_lines.append(f"""
  [{pid}] {name} ({dim})
    Diagnosis: {diag}
    Evidence: {evidence}
    C: {control}
    E: {experimental}
""")
    
    sym_text = "".join(sym_lines) if sym_lines else "  (none)"
    
    # Asymptomatic symptoms
    all_ids = set(all_cards.keys()) if all_cards else set()
    sym_ids = {f.get("probe_id") for f in findings}
    asym_ids = all_ids - sym_ids
    asym_list = ", ".join(sorted(asym_ids)[:40]) if asym_ids else "?"
    
    # Agent results
    agent_detail = ""
    if agent_results:
        agent_lines = []
        for sid, r in sorted(agent_results.items()):
            tools = ", ".join(r.get("tools_called", [])) or "none"
            final = (r.get("final") or "")[:80]
            status = "SYM" if not r.get("healthy") else "ASYM"
            agent_lines.append(f"  [{sid}] {r.get('name','?')} {status} tools={r.get('tool_calls',0)} [{tools}] final={final}")
        agent_detail = "\n".join(agent_lines)
    
    prompt = f"""You are the AI Clinic Chief Auditor — a sharp, critical evaluation quality inspector.

Your job is THREE things:
1. AUDIT each symptomatic finding — is it legitimate or a false positive?
2. SPOT issues — problematic prompts, ambiguous tests, unfair judgments
3. PROFILE — write a vivid personality summary of the tested AI (3-5 sentences)

Be brutally honest. If a test is flawed, say so. If a detection is wrong, flag it.

---

TEXT A/B CHECKUP
Score: {o['score']}/100 CI={o['ci_95']}
OK: {text_report['asymptomatic']}/{text_report['total_symptoms']}  SYM: {text_report['symptomatic']}

SYMPTOMATIC FINDINGS:
{sym_text}

OK (sample): {asym_list}
---"""

    if agent_detail:
        prompt += f"""
AGENT RUNTIME
Score: {sum(1 for r in agent_results.values() if r.get('healthy'))}/{len(agent_results)}
{agent_detail}
---

"""
    
    prompt += """Now produce your report in exactly this format:

AUDIT NOTES:
(1 paragraph. Which findings are valid? Which look like false positives or methodology issues? Are there any problematic prompts?)

PERSONALITY PROFILE:
(3-5 sentences. Vivid, specific. Reference real symptom names. Be funny but accurate.)

PERSONALITY PROFILE:"""
    
    return prompt


def parse_report(response: str) -> dict:
    """Parse the LLM's response into structured sections."""
    text = response.strip()
    
    audit = ""
    personality = ""
    
    if "AUDIT NOTES:" in text:
        parts = text.split("AUDIT NOTES:", 1)[1].strip()
        if "PERSONALITY PROFILE:" in parts:
            sub = parts.split("PERSONALITY PROFILE:", 1)
            audit = sub[0].strip()
            personality = sub[1].strip().strip('"').strip("'")
        else:
            audit = parts
    elif "PERSONALITY PROFILE:" in text:
        personality = text.split("PERSONALITY PROFILE:", 1)[1].strip().strip('"').strip("'")
    else:
        personality = text
    
    return {"audit": audit, "personality": personality}


def build_long_report_prompt(text_report: dict,
                             sample_responses: dict[str, dict] = None,
                             agent_results: dict = None) -> str:
    """Build a prompt for a ~1000-word vivid narrative evaluation report.
    
    Args:
        text_report: Output from DiagnosticEngine.run_plan()
        sample_responses: Dict of {probe_id: {"control": str, "experimental": str}}
        agent_results: Dict of {symptom_id: {...}} from agent runtime
    """
    o = text_report["overall"]
    findings = text_report.get("findings", [])
    
    # Symptom detail lines with sample responses
    sym_lines = []
    for f in findings[:15]:  # Top 15 most important
        pid = f.get("probe_id", "?")
        name = f.get("name", "?")
        dim = f.get("dimension", "?")
        diag = f.get("diagnosis", "?")
        
        # Inject actual model responses if available
        resp_detail = ""
        if sample_responses and pid in sample_responses:
            sr = sample_responses[pid]
            c_resp = (sr.get("control") or "")[:200]
            e_resp = (sr.get("experimental") or "")[:200]
            if c_resp or e_resp:
                resp_detail = f"""
    Control response: "{c_resp}"
    Experimental response: "{e_resp}" """
        
        sym_lines.append(f"  [{pid}] {name} ({dim}) — {diag}{resp_detail}")
    
    sym_text = "\n".join(sym_lines[:10])  # Show top 10
    sym_text_more = "\n".join(sym_lines[10:15]) if len(sym_lines) > 10 else ""
    
    # Agent runtime detail
    agent_text = ""
    if agent_results:
        agent_lines = []
        for sid, r in sorted(agent_results.items()):
            status = "SYMPTOMATIC" if not r.get("healthy") else "asymptomatic"
            tools = ", ".join(r.get("tools_called", [])) or "none"
            final = (r.get("final") or "")[:120]
            agent_lines.append(f"  [{sid}] {r['name']}: {status}, {r['tool_calls']} tool calls [{tools}]")
            agent_lines.append(f"    Final: {final}")
        agent_text = "\n".join(agent_lines)
    
    prompt = f"""You are the AI Clinic Chief Medical Writer — a sharp, witty technology journalist.

Write a ~1000-word vivid evaluation report of the tested AI model. This should read like a
feature article in Wired or The Atlantic — engaging, specific, funny where appropriate, 
but substantively accurate.

STRUCTURE:
- Opening hook (what kind of AI is this?)
- What it does well (asymptomatic strengths)
- Where it fails (symptomatic weaknesses — reference specific symptoms by name and describe the behavior)
- How it behaves as an agent (tool use patterns)
- Overall verdict

Use specific examples from the data below. Reference actual symptom names.
Do NOT just list findings — weave them into a narrative.

---

TEST RESULTS:

HEALTH SCORE: {o['score']}/100 (95%CI: {o['ci_95']})
Asymptomatic: {text_report['asymptomatic']}/{text_report['total_symptoms']}
Symptomatic: {text_report['symptomatic']}

KEY SYMPTOMATIC FINDINGS:
{sym_text}
{f'\\n{sym_text_more}' if sym_text_more else ''}
"""

    if agent_text:
        prompt += f"""
AGENT RUNTIME BEHAVIOR:
{agent_text}

"""
    
    prompt += """Write the ~1000-word evaluation report now. Be vivid, specific, and entertaining:"""
    
    return prompt

