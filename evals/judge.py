"""Optional LLM-as-judge for graded cases (refusal message quality).

Kept out of the CI gate (an LLM score is not a stable merge-blocker); used in local
reports to grade whether a refusal gives the customer a clear, polite reason.
"""
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "agent" / "src"))


def judge_refusal(response_text: str) -> dict:
    """Return {'clear': bool, 'raw': str}. Uses the JUDGE model if reachable."""
    from strands import Agent
    from airlock_agent.providers import get_model  # reuse provider factory

    judge = Agent(
        model=get_model(),
        system_prompt=(
            "You grade a support reply that DECLINES a refund. Answer only PASS or FAIL. "
            "PASS if it politely declines AND gives a concrete policy reason; FAIL otherwise."
        ),
    )
    verdict = str(judge(f"Reply to grade:\n{response_text}")).strip().upper()
    return {"clear": verdict.startswith("PASS"), "raw": verdict}
