"""Code-owned role capabilities and bounded static output checks.

Profiles describe the existing fixed scheduler, not executable model tools.
Checks never execute generated code or certify semantic quality, browser behavior,
or security. Changing the registry requires editing trusted application source.
"""
from __future__ import annotations

from copy import deepcopy
from html.parser import HTMLParser
import json
import re
from typing import Any

from .contracts import ROLES, canonical_hash, validate_result
from .skills import ROLE_SKILLS

VERSION = "1.0"
PHASE_ORDER = ("discovery", "decision", "build", "review")
SKILL_OWNERS = {
    "frame-opportunity": "product",
    "collect-evidence": "research",
    "specify-market": "domain",
    "select-solana-adapter": "architect",
    "parallel-build": "chief",
    "build-prediction-ui": "frontend",
    "prepare-submission": "submission",
    "verify-outcome": "reviewer",
}

# Purpose, capabilities and review questions are honest instruction-level claims.
# Accepted paths and skill IDs below come from the executable registries.
_DETAILS = {
    "research": {
        "purpose": "Turn a founder's hypothesis into an evidence map and a practical validation plan.",
        "can_do": ["Separate supplied facts, founder statements, inferences and unknowns.", "Compare the stated workaround with the proposed forecast workflow.", "Draft interview questions and a falsifiable demand test."],
        "cannot_do": ["Browse current competitors or verify linked sources.", "Conduct interviews or establish demand from the brief alone."],
        "review_questions": ["Is every factual claim traceable to supplied evidence or labeled as unverified?", "Would the proposed demand test disprove the central hypothesis if it failed?", "Are the next interviews specific enough to run with the intended users?"],
        "example": "For a launch-readiness app, identify whose decision improves, which signals they use today, and how three interviews could invalidate the idea.",
    },
    "product": {
        "purpose": "Define one complete user journey with observable success and failure states.",
        "can_do": ["Translate the frozen brief into a scoped product specification.", "Specify the forecast, close, resolution and calibration journey.", "Write user stories, acceptance criteria and explicit exclusions."],
        "cannot_do": ["Change the approved question or expand into real-money trading.", "Read discovery outputs that are produced concurrently."],
        "review_questions": ["Does the journey solve the user's stated decision rather than merely display probabilities?", "Do stories include failure, empty and ambiguous-outcome states?", "Is the scope possible within one self-contained simulation?"],
        "example": "Define how a builder records a launch forecast, closes entries, attests an outcome and learns from the resulting calibration.",
    },
    "architect": {
        "purpose": "Choose the smallest credible architecture and identify the proof needed for Solana integration.",
        "can_do": ["Distinguish the local coordinator, generated browser app and future chain adapter.", "Describe required provider capabilities and trust boundaries.", "List the source, license, network and transaction evidence a future adapter needs."],
        "cannot_do": ["Inspect a live RPC, deploy a program or verify a transaction.", "Treat a planned adapter or wallet button as implemented settlement."],
        "review_questions": ["Is each component labeled as implemented, simulated or proposed?", "Is Solana's intended purpose useful to this user journey?", "Are integration blockers and the evidence required to remove them explicit?"],
        "example": "Explain whether a forecast registry is sufficient before proposing exchange mechanics, then list the devnet transaction proof still needed.",
    },
    "chief": {
        "purpose": "Resolve discovery tradeoffs into a bounded decision for founder approval.",
        "can_do": ["Read and reconcile the three accepted discovery artifacts.", "Name contradictions, the largest uncertainty and the cuts needed for one useful flow.", "Write an approval memo tied to the frozen brief."],
        "cannot_do": ["Approve its own memo or bypass the founder gate.", "Authorize spend, alter the brief or create additional workers."],
        "review_questions": ["Does the memo resolve disagreements instead of copying three recommendations?", "Is the exact scope being approved clear?", "Would a stop recommendation be understandable if evidence is insufficient?"],
        "example": "Recommend a simulation-first launch forecast, defer custody and oracles, and surface the one unresolved decision the founder must approve.",
    },
    "frontend": {
        "purpose": "Generate a self-contained browser simulation that makes the approved journey usable.",
        "can_do": ["Adapt the reference HTML to the approved audience and question.", "Implement forecast entry, manual close, YES/NO/VOID resolution and calibration in browser code.", "Provide responsive layout, keyboard labels and honest simulation cues."],
        "cannot_do": ["Execute generated code or verify its browser behavior.", "Add remote assets, fetch APIs, wallet access or a hidden Studio connection.", "Read the market designer's concurrently produced files."],
        "review_questions": ["Can a keyboard user complete the whole journey and understand each state?", "Do YES, NO and VOID produce correct behavior and meaningful feedback?", "Does the layout remain readable on mobile with clear simulation labels?"],
        "example": "Build a working local forecast interaction for the frozen question, then leave browser and numerical verification to executable tests or a human reviewer.",
    },
    "domain": {
        "purpose": "Preserve the approved question and define how outcomes are resolved without ambiguity.",
        "can_do": ["Emit a machine-readable contract bound to the frozen question, resolution rule and void policy.", "Explain closing, attestation, disputes, missing evidence and ambiguous outcomes.", "Keep outcome vocabulary explicit: YES, NO and VOID."],
        "cannot_do": ["Resolve an external event or fetch an oracle.", "Convert a forecast average into a trade price or settle money.", "Silently reinterpret the approved resolution or void rule."],
        "review_questions": ["Would two independent readers resolve the same evidence to the same outcome?", "Are closing time, authoritative evidence, finality and disputes specified or clearly unresolved?", "Does VOID cover unavailable or ambiguous evidence without inventing certainty?"],
        "example": "Keep the founder's launch-date rule exact in market.json, then identify timezone, evidence source or finality details that still need agreement.",
    },
    "submission": {
        "purpose": "Turn the approved plan into an honest pitch, walkthrough and application draft.",
        "can_do": ["Write three separate draft artifacts for the founder to review.", "Explain user pain, differentiation hypotheses, architecture and the proposed demo.", "Mark implementation claims and missing submission details as pending."],
        "cannot_do": ["Observe concurrent build results or claim they passed.", "Verify current portal requirements, invent traction or submit an application."],
        "review_questions": ["Are every implementation, traction and team claim supported or labeled pending?", "Are the pitch and technical walkthrough appropriate for their different audiences?", "Are missing URLs, eligibility and portal checks clearly assigned for follow-up?"],
        "example": "Draft a two-minute launch-forecast story and a separate technical walkthrough without asserting that the parallel build or chain integration is verified.",
    },
    "reviewer": {
        "purpose": "Challenge the accepted artifacts and identify evidence-backed blockers.",
        "can_do": ["Read all ten accepted artifacts, including generated HTML, plus the static verification report.", "Find inconsistencies, unsupported claims and unresolved user or resolution risks.", "Separate blocking findings, useful improvements and deferred work."],
        "cannot_do": ["Run browser, shell, web or chain checks.", "Certify security, override failed checks or repair another role's artifacts.", "Claim a separate provider or independent model; the live workflow shares one configured model."],
        "review_questions": ["Does each finding identify an artifact, concrete issue and consequence?", "Are static checks distinguished from tests that were never run?", "Does the review challenge unsupported claims instead of assigning a decorative score?"],
        "example": "Compare the UI, market contract and pitch; flag a claimed oracle that the architecture still lists as future work.",
    },
}
_COMMON_LIMITS = ["Model requests have no browser, shell, filesystem, wallet or search tools.", "Only the coordinator can write accepted files; model output cannot change permissions."]
_CHECKS = {
    "output-contract": "Exact owned files, valid result structure, nonempty content and size/credential guards",
    "market-json": "Market JSON is an object with unique keys and finite JSON values",
    "market-brief": "Question, resolution rule and void policy exactly match the frozen brief",
    "market-mode": "Market mode is offchain-simulation and outcomes are YES, NO, VOID",
    "html-document": "Complete HTML document has a language, nonempty title and mobile viewport",
    "html-resources": "No declared external resources or obvious network calls in the source",
}


def profile_for(role: str) -> dict:
    """Return a defensive, JSON-safe description of one trusted role contract."""
    if role not in ROLES or role not in _DETAILS:
        raise ValueError("Unknown capability role")
    spec = ROLES[role]
    phase = PHASE_ORDER.index(spec["phase"])
    paths = [path for definition in ROLES.values()
             if PHASE_ORDER.index(definition["phase"]) < phase
             for path in definition["paths"]]
    check_ids = ["output-contract"]
    if role == "domain":
        check_ids += ["market-json", "market-brief", "market-mode"]
    if role == "frontend":
        check_ids += ["html-document", "html-resources"]
    details = deepcopy(_DETAILS[role])
    details["cannot_do"] += _COMMON_LIMITS
    return {"version": VERSION, "id": role, "name": spec["name"], "phase": spec["phase"],
            **details, "input_context": "Frozen founder brief plus the accepted files listed here. Inputs are fixed before each parallel wave; peer outputs are not visible during that wave." +
            (" The reviewer also receives the deterministic verification report." if role == "reviewer" else ""),
            "execution": "Instruction-based generation: scripted fixtures in rehearsal; one request to the shared configured model in live mode. No executable model tools.",
            "input_paths": paths, "output_paths": list(spec["paths"]),
            "skill_ids": list(ROLE_SKILLS[role]),
            "acceptance_checks": [{"id": key, "label": _CHECKS[key], "kind": "static"} for key in check_ids]}


def profile_hash(role: str) -> str:
    return canonical_hash(profile_for(role))


def all_profiles() -> list[dict]:
    return [profile_for(role) for role in ROLES]


def _strict_json(content: str) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    def constant(_):
        raise ValueError("Non-finite JSON value")
    # parse_float also rejects overflow such as 1e999, not only NaN/Infinity.
    def decimal(value):
        parsed = float(value)
        if parsed == float("inf") or parsed == float("-inf"):
            raise ValueError("Non-finite JSON value")
        return parsed
    return json.loads(content, object_pairs_hook=pairs, parse_constant=constant, parse_float=decimal)


class _HTMLSource(HTMLParser):
    """Collect syntax for narrow source checks; this is not a browser parser."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.doctype = False
        self.starts = {name: 0 for name in ("html", "head", "body", "title")}
        self.ends = dict(self.starts)
        self.sequence = []
        self.lang = ""
        self.viewport = False
        self.title = []
        self.active = []
        self.script = []
        self.css = []
        self.resources = []
        self.foreign_depth = 0

    def handle_decl(self, decl):
        self.doctype = self.doctype or decl.strip().lower() == "doctype html"

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in ('svg', 'math'):
            self.foreign_depth += 1
        if tag in self.starts and not self.foreign_depth:
            self.starts[tag] += 1
            self.sequence.append("start:" + tag)
        if tag == "html" and not self.foreign_depth:
            self.lang = values.get("lang") or ""
        if tag == "meta":
            if (values.get("name") or "").lower() == "viewport":
                self.viewport = bool(re.search(r"(?:^|[,;\s])width\s*=\s*device-width(?:$|[,;\s])", values.get("content") or "", re.I))
            if (values.get("http-equiv") or "").lower() == "refresh":
                self.resources.append("meta refresh")
        if tag in ("base", "iframe", "frame", "object", "embed"):
            self.resources.append(tag + " element")
        for name, value in attrs:
            value = (value or "").strip()
            # A URL literal in text or a normal link is not a resource import.
            if name in ("src", "srcset", "poster", "background", "action", "formaction", "ping") or (name == "href" and tag == "link"):
                if value and (tag == "script" or name == "srcset" or not value.lower().startswith("data:")):
                    self.resources.append(tag + "[" + name + "]")
            if tag in ("image", "use") and name in ("href", "xlink:href") and value and not value.lower().startswith(("data:", "#")):
                self.resources.append(tag + "[" + name + "]")
            if name == "href" and value.lower().startswith("javascript:"):
                self.script.append(value.partition(":")[2])
            if name == "style":
                self.css.append(value)
            if name.startswith("on"):
                self.script.append(value)
        if tag in ("script", "style", "title"):
            self.active.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in self.ends and not self.foreign_depth:
            self.ends[tag] += 1
            self.sequence.append("end:" + tag)
        if self.active and self.active[-1] == tag:
            self.active.pop()
        if tag in ('svg', 'math') and self.foreign_depth:
            self.foreign_depth -= 1

    def handle_data(self, data):
        if not self.active:
            return
        if self.active[-1] == "title" and not self.foreign_depth:
            self.title.append(data)
        elif self.active[-1] == "script":
            self.script.append(data)
        elif self.active[-1] == "style":
            self.css.append(data)

    def document_ok(self):
        expected = ["start:html", "start:head", "start:title", "end:title", "end:head", "start:body", "end:body", "end:html"]
        return (self.doctype and all(value == 1 for value in self.starts.values()) and
                all(value == 1 for value in self.ends.values()) and self.sequence == expected and
                bool(self.lang.strip()) and bool("".join(self.title).strip()) and self.viewport)

    def source_indicators(self):
        indicators = list(self.resources)
        css = "\n".join(self.css)
        if re.search(r"@import\b", css, re.I):
            indicators.append("CSS import")
        for match in re.finditer(r"url\s*\(\s*(['\"]?)(.*?)\1\s*\)", css, re.I | re.S):
            if not match.group(2).strip().lower().startswith(("data:", "#")):
                indicators.append("CSS resource URL")
        js = "\n".join(self.script)
        gap = r"(?:\s|/\*[\s\S]*?\*/|//[^\n]*\n)*"
        if re.search(r"\bimport" + gap + r"(?:\(|[\"'{*]|[A-Za-z_$][\w$]*\s+from\b)", js):
            indicators.append("JavaScript import")
        if re.search(r"\bexport" + gap + r"(?:\*|\{[^}]*\})" + gap + r"from\b", js):
            indicators.append("JavaScript re-export")
        if re.search(r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon)" + gap + r"\(", js):
            indicators.append("JavaScript network API")
        return sorted(set(indicators))


def validate_role_output(role: str, raw: Any, brief: dict) -> dict:
    """Return a non-executing acceptance report; do not publish failed artifacts.

    Static checks describe only what they observe. Human review questions in each
    profile remain unanswered even when all checks pass. Source indicator checks
    are conservative and cannot discover obfuscated or computed network behavior.
    """
    checks = []
    def record(key, passed, detail):
        checks.append({"id": key, "label": _CHECKS[key], "passed": bool(passed), "detail": detail})
    not_tested = ["Usefulness, factual accuracy and completeness of written analysis", "Generated app behavior, accessibility and numerical correctness in a browser", "Obfuscated or computed network behavior and production security", "Live provider output quality, external facts and Solana execution"]
    try:
        result = validate_result(role, raw)
    except (ValueError, TypeError, KeyError, RecursionError, UnicodeError):
        record("output-contract", False, "Result does not satisfy this role's owned-file and structured-output contract.")
        return {"kind": "role-output-checks", "version": VERSION, "passed": False, "checks": checks, "not_tested": not_tested}
    record("output-contract", True, "All required owned files are present and satisfy the shared output guards.")
    artifacts = {item["path"]: item["content"] for item in result["artifacts"]}
    if role == "domain":
        try:
            market = _strict_json(artifacts["app/market.json"])
            parsed = isinstance(market, dict)
        except (ValueError, TypeError, RecursionError, OverflowError):
            market, parsed = {}, False
        record("market-json", parsed, "Unique-key JSON object with finite values." if parsed else "Expected a JSON object without duplicate keys, NaN, Infinity or overflowing numbers.")
        mapping = {"question": "market_question", "resolution_rule": "resolution_rule", "void_policy": "void_policy"}
        matches = parsed and isinstance(brief, dict) and all(isinstance(market.get(key), str) and isinstance(brief.get(source), str) and bool(brief[source].strip()) and market[key] == brief[source] for key, source in mapping.items())
        record("market-brief", matches, "All three strings match the frozen brief exactly." if matches else "Question, resolution rule and void policy must be strings copied exactly from the frozen brief.")
        mode = parsed and market.get("mode") == "offchain-simulation" and market.get("outcomes") == ["YES", "NO", "VOID"]
        record("market-mode", mode, "Simulation mode and ordered outcome vocabulary are explicit." if mode else "Expected offchain-simulation and outcomes [YES, NO, VOID].")
    if role == "frontend":
        source = _HTMLSource()
        try:
            source.feed(artifacts["app/index.html"])
            source.close()
            document_ok = source.document_ok()
            indicators = source.source_indicators()
        except (ValueError, TypeError, RecursionError):
            document_ok, indicators = False, ["HTML parse failure"]
        record("html-document", document_ok, "One HTML/head/body document, language, title and width=device-width viewport found." if document_ok else "Expected one complete HTML document with doctype, language, head/title, body and mobile viewport.")
        record("html-resources", not indicators, "No declared resource or network API indicators found; this does not prove absence of network behavior." if not indicators else "Source indicators found: " + ", ".join(indicators) + ". Embedded-only source is required; computed behavior remains untested.")
    return {"kind": "role-output-checks", "version": VERSION, "passed": all(check["passed"] for check in checks), "checks": checks, "not_tested": not_tested}
