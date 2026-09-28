"""Providers return typed artifacts. Neither provider can execute generated code."""
from __future__ import annotations
import asyncio
import html
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def render_reference_app(brief: dict) -> str:
    text = (ROOT / "templates/reference-app.html").read_text()
    for key in ("project_name", "market_question", "resolution_rule", "void_policy", "template"):
        text = text.replace("{{" + key + "}}", html.escape(brief[key], quote=True))
    return text


class RehearsalProvider:
    """Scripted fixtures, not AI inference. Uses the same scheduler and permissions."""
    name = "rehearsal"
    def __init__(self, delay: float = 0.65):
        self.delay = delay

    async def run(self, role: str, brief: dict, context: str) -> tuple[dict, dict]:
        await asyncio.sleep(self.delay)
        name = brief["project_name"]
        files = {
            "research": {"research/market.md": f"# Evidence synthesis — {name}\n\nSCRIPTED REHEARSAL, not market research.\n\nTarget: {brief['user']}\n\nProblem hypothesis: {brief['problem']}\n\nCurrent alternative: {brief['alternative']}\n\nNo interviews, market sizing or demand validation were performed. Interview three intended users before making traction claims.\n"},
            "product": {"product/spec.md": f"# Product contract\n\nUser: {brief['user']}\n\nOne flow: understand the question → record a forecast → close forecasting → record a human-attested outcome → inspect calibration.\n\nDifference hypothesis: {brief['difference']}\n\nNot built: wallets, real-money trading, automatic oracles, distribution or payments.\n"},
            "architect": {"architecture/plan.md": "# Architecture\n\nLocal browser-only reference app; no Solana connection yet.\n\nNext engineering gate: replace the simulation adapter with one reviewed provider or a dedicated devnet forecast registry. Establish the protocol, cluster, IDL, license, account ownership and transaction checks first. A wallet connection or memo transaction does not make the market on-chain.\n\nDo not assume a mainnet prediction provider supports devnet or custom market creation.\n"},
            "chief": {"decisions/build-memo.md": f"# Founder decision\n\nBuild {name} for {brief['user']}.\n\nApprove only a local simulated forecast application and draft submission assets. The brief is a hypothesis, not evidence.\n\nResolution: {brief['resolution_rule']}\n\nVoid: {brief['void_policy']}\n\nPreserve one useful flow. Defer money, custody, autonomous trading and public release. Solana integration remains a release blocker.\n"},
            "frontend": {"app/index.html": render_reference_app(brief)},
            "domain": {"app/market.json": json.dumps({"question": brief["market_question"], "resolution_rule": brief["resolution_rule"], "void_policy": brief["void_policy"], "mode": "offchain-simulation", "outcomes": ["YES", "NO", "VOID"]}, indent=2), "domain/resolution.md": f"# Resolution contract\n\n{brief['resolution_rule']}\n\nInvalid / ambiguous outcome: {brief['void_policy']}\n\nThis rehearsal uses a human-attested outcome. It does not fetch an oracle, prove facts, issue tokens or settle money. Do not equate a mean forecast with an executable market price.\n"},
            "submission": {"submission/pitch.md": f"# {name} — pitch working draft\n\n0:00 User and pain: {brief['user']}; {brief['problem']}\n\n0:30 Approach: {brief['why_prediction']}\n\n1:00 Demonstrate the local simulation. Label it accurately.\n\n1:40 Differentiation hypothesis: {brief['difference']}\n\n2:05 Intended Solana role: {brief['why_solana']} — not implemented in this run.\n\n2:30 Team, evidence and next milestone. User counts and traction: NOT MEASURED.\n", "submission/demo.md": "# Technical walkthrough\n\nShow the frozen brief, parallel task timestamps, founder approval, generated artifacts, reference app and static check report. Clearly distinguish scripted rehearsal from paid model execution.\n\nDo not substitute this for a real Solana transaction demonstration. Record the chain-integrated demo only after verifying it.\n", "submission/application.md": f"# Application draft — {name}\n\nStatus: NOT SUBMITTED.\n\nProblem: {brief['problem']}\n\nUser: {brief['user']}\n\nClaims requiring evidence: chain integration, user validation, live model run, business demand.\n\nTeam members, repository URL, accessible videos, current portal fields and organizer eligibility confirmation must be completed by the humans.\n"},
            "reviewer": {"qa/review.md": "# Independent review fixture\n\nSCRIPTED REHEARSAL; not an actual model review.\n\nBlocking official-submission claims: no verified Solana integration, no paid multi-agent run, no participant outcomes measured, videos not recorded.\n\nThe deterministic check report only checks artifact contracts. It does not certify product correctness or security.\n"},
        }[role]
        return {"summary": f"Scripted {role} artifacts written; not an AI result.", "artifacts": [{"path": k, "content": v} for k, v in files.items()], "limitations": ["Scripted rehearsal", "No blockchain connection"]}, {"input_tokens": 0, "output_tokens": 0, "requests": 0, "provider": self.name, "response_ids": []}

