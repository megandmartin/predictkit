"""Read-only catalog of packaged role prompts and explicitly allowed skill files.

This reports instructions available to request assembly, not proof that a model
used them. It never loads global skills, credentials, run data or arbitrary paths.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re

from .contracts import ROLES, safe_path
from .skills import ROLE_SKILLS
from .capabilities import profile_for, SKILL_OWNERS

ROOT = Path(__file__).resolve().parents[1]
MAX_PROMPT_BYTES = 20_000
OPERATOR_GUIDES = ("run-workshop", "continue-sprint")
# These are the fixed scheduler's phases; role membership comes from ROLES.
PHASE_ORDER = ("discovery", "decision", "build", "review")
_IDENTIFIER = re.compile(r"[a-z][a-z0-9-]*\Z")


def _read_prompt(root: Path, relative: str) -> tuple[str, str]:
    """Read only a caller-selected catalog entry, rejecting symlink components."""
    if root.is_symlink():
        raise ValueError("Catalog root must not be a symlink")
    path = safe_path(root, relative)
    if not path.is_file() or path.stat().st_size > MAX_PROMPT_BYTES:
        raise ValueError(f"Catalog prompt missing or oversized: {relative}")
    content = path.read_bytes()
    if len(content) > MAX_PROMPT_BYTES:
        raise ValueError(f"Catalog prompt oversized: {relative}")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError(f"Catalog prompt must be UTF-8: {relative}") from None
    if not text.strip():
        raise ValueError(f"Catalog prompt is empty: {relative}")
    return text, hashlib.sha256(content).hexdigest()


def _skill(root: Path, identifier: str) -> dict:
    if not _IDENTIFIER.fullmatch(identifier):
        raise ValueError("Invalid packaged skill identifier")
    path = f"skills/{identifier}/SKILL.md"
    content, digest = _read_prompt(root, path)
    # The bundled skills use this deliberately small, single-line frontmatter
    # contract. No YAML objects, executable tags or remote includes are loaded.
    if not content.startswith("---\n") or "\n---\n" not in content[4:]:
        raise ValueError(f"Catalog skill metadata missing: {path}")
    frontmatter = content[4:].split("\n---\n", 1)[0]
    metadata = {}
    for line in frontmatter.splitlines():
        key, separator, value = line.partition(":")
        if key in ("name", "description") and separator:
            if key in metadata:
                raise ValueError(f"Duplicate catalog skill metadata: {path}")
            metadata[key] = value.strip()
    if metadata.get("name") != identifier or not metadata.get("description"):
        raise ValueError(f"Catalog skill metadata invalid: {path}")
    return {"id": identifier, "name": metadata["name"],
            "description": metadata["description"], "path": path,
            "content": content, "sha256": digest}


def build_catalog(root: Path = ROOT) -> dict:
    """Return the source-backed catalog; ``root`` is only for trusted local use.

    HTTP callers must not supply a root or filename. Entries are selected from
    the runtime role/skill registries plus the two named operator guides. Added
    files elsewhere in the checkout cannot enter this response automatically.
    """
    root = Path(root)
    if set(ROLES) != set(ROLE_SKILLS):
        raise ValueError("Role and skill registries disagree")
    roles = []
    for identifier, definition in ROLES.items():
        if not _IDENTIFIER.fullmatch(identifier) or definition["phase"] not in PHASE_ORDER:
            raise ValueError("Invalid packaged role definition")
        role_path = f"agents/{identifier}.md"
        content, _ = _read_prompt(root, role_path)
        marker = "## Mission\n"
        if marker not in content:
            raise ValueError(f"Catalog role mission missing: {role_path}")
        summary = " ".join(content.split(marker, 1)[1].split("\n## ", 1)[0].split())
        if not summary:
            raise ValueError(f"Catalog role mission empty: {role_path}")
        phase_index = PHASE_ORDER.index(definition["phase"])
        previous_phase = PHASE_ORDER[phase_index - 1] if phase_index else None
        roles.append({"id": identifier, "title": definition["name"], "summary": summary,
                      "phase": definition["phase"], "role_path": role_path,
                      "role_content": content,
                      "depends_on": [role for role, spec in ROLES.items()
                                     if spec["phase"] == previous_phase],
                      "outputs": list(definition["paths"]), "skills": list(ROLE_SKILLS[identifier]),
                      "capability": profile_for(identifier)})
    skill_ids = list(dict.fromkeys(skill for role in ROLES for skill in ROLE_SKILLS[role]))
    if set(skill_ids).intersection(OPERATOR_GUIDES):
        raise ValueError("Operator guide is now role-loaded; update catalog classification")
    return {
        "roles": roles,
        "skills": [{**_skill(root, identifier), 'primary_role': SKILL_OWNERS[identifier],
                    'used_by': [role for role in ROLES if identifier in ROLE_SKILLS[role]]} for identifier in skill_ids],
        "operator_guides": [_skill(root, identifier) for identifier in OPERATOR_GUIDES],
        "runtime_modes": [
            {"id": "rehearsal", "title": "Local rehearsal", "uses_ai": False,
             "provider": "rehearsal", "tools": [], "model_selection": "No model",
             "summary": "The real Python scheduler writes scripted template outputs. No AI or provider requests."},
            {"id": "openai", "title": "Live OpenAI API", "uses_ai": True,
             "provider": "openai-responses", "tools": [],
             "model_selection": "One explicitly configured PREDICTKIT_MODEL for every role",
             "summary": "Separate stateless Responses API requests receive role prompts, mapped skills and accepted artifacts. Model access, rates, budget and paid-run approval are required."},
        ],
        "capability_summary": {
            "coordinator": "Deterministic Python code schedules fixed waves, validates outputs, writes files and records evidence.",
            "roles": "Roles are instructions and output contracts; they share the configured provider and model.",
            "skills": "Eight mapped skills are appended as prompt text in live requests. Two operator guides are packaged but not loaded into role requests.",
            "defaults": "Rehearsal is the default. There is no default live model or automatic paid call.",
            "context": "Each live request receives the frozen brief and accepted artifacts selected by the coordinator; it does not inherit a Codex or Claude chat.",
            "tools": "Model roles have no browser, shell, filesystem, wallet or search tools. The server does not execute their generated code.",
            "coding_assistants": "Codex and Claude can help edit and run the repository as development assistants. Native Codex or Claude workers and subscription sign-in are not integrated runtime providers.",
            "global_skills": "Skills installed in a coding assistant elsewhere on the laptop are not automatically packaged or loaded by PredictKit.",
            "evidence": "The catalog shows available source instructions. A catalog entry or file hash does not prove a live model run or instruction compliance.",
            "sources": ["predictkit/contracts.py", "predictkit/skills.py", "predictkit/runtime.py",
                        "predictkit/providers.py", "predictkit/http_provider.py", "predictkit/server.py"],
        },
    }
