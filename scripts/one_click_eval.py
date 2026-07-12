"""One-click: run checkup → generate long report → update leaderboard."""
import asyncio, os, sys, json, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()

async def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "deepseek-v4-flash"
    plan = sys.argv[2] if len(sys.argv) > 2 else "all"
    samples = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    judge = sys.argv[4] if len(sys.argv) > 4 else "deepseek-v4-flash"
    
    t0 = time.time()
    safe = model.replace("-", "_")
    
    # Step 1: Run checkup
    print(f"\n{'='*60}")
    print(f"  Step 1/3: Running checkup on {model} ({plan}, {samples}samples)")
    print(f"{'='*60}")
    rc = os.system(f"ai-clinic check {model} --plan {plan} --samples {samples} --judge {judge} --save evaluations/{safe}_full.json")
    if rc != 0:
        print(f"  Checkup failed (exit code {rc})")
        return
    
    # Step 2: Generate long report
    print(f"\n{'='*60}")
    print(f"  Step 2/3: Generating clinical report")
    print(f"{'='*60}")
    rc = os.system(f"cd {os.path.dirname(os.path.dirname(__file__))} && py scripts/gen_report.py evaluations/{safe}_full.json {model} {judge}")
    if rc != 0:
        print(f"  Report generation failed (exit code {rc})")
        # Continue anyway — report is optional
    
    # Step 3: Embed and update leaderboard
    print(f"\n{'='*60}")
    print(f"  Step 3/3: Updating leaderboard")
    print(f"{'='*60}")
    rc = os.system(f"cd {os.path.dirname(os.path.dirname(__file__))} && py scripts/embed_symptoms.py")
    if rc != 0:
        print(f"  Leaderboard update failed (exit code {rc})")
    
    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"  All done in {elapsed:.0f}s")
    print(f"  Results: evaluations/{safe}_full.json")
    print(f"  Report:  evaluations/{safe}_long_report.json")
    print(f"  Leaderboard updated")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())
