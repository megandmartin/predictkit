"""Deterministic boundaries. Instructions alone are not permissions."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

ROLES = {
    "research": {"name": "Evidence lead", "phase": "discovery", "paths": ["research/market.md"]},
    "product": {"name": "Product lead", "phase": "discovery", "paths": ["product/spec.md"]},
    "architect": {"name": "Solana architect", "phase": "discovery", "paths": ["architecture/plan.md"]},
    "chief": {"name": "Chief of staff", "phase": "decision", "paths": ["decisions/build-memo.md"]},
    "frontend": {"name": "App engineer", "phase": "build", "paths": ["app/index.html"]},
    "domain": {"name": "Market designer", "phase": "build", "paths": ["app/market.json", "domain/resolution.md"]},
    "submission": {"name": "Submission lead", "phase": "build", "paths": ["submission/pitch.md", "submission/demo.md", "submission/application.md"]},
    "reviewer": {"name": "Independent reviewer", "phase": "review", "paths": ["qa/review.md"]},
}
REQUIRED = ["project_name", "user", "problem", "industry", "alternative", "why_prediction", "why_solana", "difference", "market_question", "resolution_rule", "void_policy"]
TEMPLATES = {"forecast-studio", "market-explorer", "resolution-desk"}
MAX_FILE_BYTES = 150_000
MAX_JOB_BYTES = 350_000


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def validate_brief(raw: Any) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("Brief must be a JSON object")
    clean = {}
    for key in REQUIRED:
        value = raw.get(key)
        if not isinstance(value, str) or not 3 <= len(value.strip()) <= 2500:
            raise ValueError(f"{key}: enter 3–2500 characters")
        clean[key] = value.strip()
    template = raw.get("template", "forecast-studio")
    if template not in TEMPLATES:
        raise ValueError("Unknown template")
    clean["template"] = template
    clean["network"] = "offchain-simulation"  # Cannot be promoted by a prompt.
    return clean


def safe_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or "\x00" in relative:
        raise ValueError("Invalid artifact path")
    p = PurePosixPath(relative)
    if p.is_absolute() or any(part in ("..", ".") for part in relative.split("/")):
        raise ValueError("Path traversal rejected")
    if any(part.startswith(".") for part in p.parts):
        raise ValueError("Hidden paths are not artifact destinations")
    root = root.resolve()
    target = root.joinpath(*p.parts)
    current = root
    for part in p.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Symlinks are not allowed in artifact paths")
    if not target.resolve().is_relative_to(root):
        raise ValueError("Artifact escaped its workspace")
    return target


def validate_result(role: str, raw: Any) -> dict:
    if role not in ROLES or not isinstance(raw, dict):
        raise ValueError("Invalid role/result")
    if set(raw) != {"summary", "artifacts", "limitations"}:
        raise ValueError("Result requires summary, artifacts and limitations only")
    if not isinstance(raw["summary"], str) or len(raw["summary"]) > 3000:
        raise ValueError("Invalid summary")
    if not isinstance(raw["limitations"], list) or not all(isinstance(x, str) and len(x) <= 3000 for x in raw["limitations"]):
        raise ValueError("Invalid limitations")
    artifacts = raw["artifacts"]
    expected = set(ROLES[role]["paths"])
    if not isinstance(artifacts, list) or len(artifacts) != len(expected):
        raise ValueError("Missing or extra role artifacts")
    seen, total = set(), 0
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != {"path", "content"}:
            raise ValueError("Artifact must contain path and content")
        path, content = artifact["path"], artifact["content"]
        if path not in expected or path in seen:
            raise ValueError("Ownership conflict or duplicate artifact")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Empty artifact")
        size = len(content.encode())
        total += size
        if size > MAX_FILE_BYTES or total > MAX_JOB_BYTES:
            raise ValueError("Artifact size limit exceeded")
        if re.search(r"sk-(?:proj-)?[A-Za-z0-9_-]{24,}", content):
            raise ValueError("Possible credential in artifact; output quarantined")
        if path.endswith(".json"):
            json.loads(content)
        seen.add(path)
    if seen != expected:
        raise ValueError("Role did not produce its complete contract")
    return raw


def verify_artifacts(root: Path) -> dict:
    """Static evidence only, never described as a browser or chain test."""
    checks = []
    for role in ("research", "product", "architect", "chief", "frontend", "domain", "submission"):
        for path in ROLES[role]["paths"]:
            target = safe_path(root, path)
            checks.append({"name": f"Artifact exists: {path}", "passed": target.is_file() and target.stat().st_size > 0})
    html_path = root / "app/index.html"
    html = html_path.read_text() if html_path.exists() else ""
    checks.append({"name": "App has a document body", "passed": "<body" in html.lower() and "</html>" in html.lower()})
    checks.append({"name": "App declares simulation status", "passed": "simulation" in html.lower()})
    try:
        market = json.loads((root / "app/market.json").read_text())
        required = {"question", "resolution_rule", "void_policy", "mode", "outcomes"}
        valid = required.issubset(market) and market["mode"] == "offchain-simulation" and market["outcomes"] == ["YES", "NO", "VOID"]
    except (ValueError, OSError, TypeError):
        valid = False
    checks.append({"name": "Market contract is explicit and simulation-only", "passed": valid})
    return {"kind": "static-contract-checks", "passed": all(x["passed"] for x in checks), "checks": checks,
            "not_tested": ["Generated live app browser behavior", "Solana transactions", "External prediction providers", "Legal eligibility", "Production security"]}
