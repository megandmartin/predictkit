"""A small, fixed sprint graph; not a general autonomous company framework."""
from __future__ import annotations
import asyncio
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
import threading
import time
import uuid
import zipfile

from .contracts import ROLES, MAX_FILE_BYTES, validate_brief, validate_result, safe_path, canonical_hash, verify_artifacts

TERMINAL = {"idle", "packaged", "needs_fixes", "failed", "stopped", "interrupted"}
RUN_ID = re.compile(r"[0-9]{8}T[0-9]{6}-[a-f0-9]{8}")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: object):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("Symlink state path rejected")
    fd, temporary = tempfile.mkstemp(prefix=".state-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(value, out, indent=2, ensure_ascii=False)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class SprintEngine:
    def __init__(self, root: Path, provider, *, concurrency: int = 3, timeout: float = 150,
                 max_calls: int = 10, max_elapsed: float = 7200):
        if not 1 <= concurrency <= 3:
            raise ValueError("Concurrency must be 1–3")
        self.root, self.provider = root.resolve(), provider
        self.root.mkdir(parents=True, exist_ok=True)
        self.concurrency, self.timeout, self.max_calls = concurrency, timeout, max_calls
        self.max_elapsed = max_elapsed
        self.lock = threading.RLock()
        self.cancelled, self.paused, self.approval = threading.Event(), threading.Event(), threading.Event()
        self.thread = None
        self.state = {"id": None, "status": "idle", "provider": provider.name, "jobs": {}, "events": [],
                      "artifacts": [], "usage": {"input_tokens": 0, "output_tokens": 0, "requests": 0}, "calls_started": 0}
        self.directory = None
        self._recover()

    def _saved(self, identifier):
        if not isinstance(identifier, str) or not RUN_ID.fullmatch(identifier):
            raise ValueError("Invalid run identifier")
        directory = safe_path(self.root, identifier)
        target = safe_path(directory, "state.json")
        if target.stat().st_size > 4_000_000:
            raise ValueError("Saved run is oversized")
        state = json.loads(target.read_text())
        if not isinstance(state, dict) or state.get("id") != identifier:
            raise ValueError("Invalid saved run")
        if canonical_hash(state.get("brief")) != state.get("brief_hash"):
            raise ValueError("Saved brief integrity mismatch")
        if (not isinstance(state.get("jobs"), dict) or set(state["jobs"]) != set(ROLES) or
            any(not isinstance(job, dict) for job in state["jobs"].values()) or
            not isinstance(state.get("events"), list) or any(not isinstance(event, dict) for event in state["events"]) or
            not isinstance(state.get("artifacts"), list) or len(state["artifacts"]) > 11):
            raise ValueError("Invalid saved run evidence")
        owners = {path: role for role, spec in ROLES.items() for path in spec["paths"]}
        seen = set()
        for entry in state["artifacts"]:
            if (not isinstance(entry, dict) or not isinstance(entry.get("path"), str) or
                entry["path"] not in owners or entry["path"] in seen or entry.get("owner") != owners[entry["path"]]):
                raise ValueError("Invalid saved artifact inventory")
            seen.add(entry["path"])
        return directory, state

    def _recover(self):
        saved = []
        for entry in self.root.iterdir():
            if not RUN_ID.fullmatch(entry.name):
                continue
            try:
                directory, state = self._saved(entry.name)
                if state.get("status") not in TERMINAL:
                    state.update(status="interrupted", paused=False)
                    for job in state["jobs"].values():
                        if job.get("status") == "running":
                            job["status"] = "interrupted"
                    event = {"seq": len(state["events"]) + 1, "at": utcnow(), "kind": "sprint.interrupted",
                             "message": "Runtime restarted. Existing evidence is inspectable; no provider call was restarted."}
                    state["events"].append(event)
                    with safe_path(directory, "events.jsonl").open("a", encoding="utf-8") as out:
                        out.write(json.dumps(event) + "\n")
                    atomic_json(directory / "state.json", state)
                saved.append((state.get("created_at", ""), directory, state))
            except (OSError, ValueError, TypeError, KeyError):
                continue
        if saved:
            _, self.directory, self.state = max(saved, key=lambda item: item[0])

    def history(self):
        with self.lock:
            runs = []
            for entry in self.root.iterdir():
                if not RUN_ID.fullmatch(entry.name):
                    continue
                try:
                    _, state = self._saved(entry.name)
                    runs.append({"id": state["id"], "status": state["status"], "provider": state["provider"],
                                 "project_name": state["brief"]["project_name"], "created_at": state["created_at"]})
                except (OSError, ValueError, TypeError, KeyError):
                    continue
            return {"runs": sorted(runs, key=lambda item: item["created_at"], reverse=True), "selected_id": self.state.get("id")}

    def select(self, identifier):
        with self.lock:
            if self.thread and self.thread.is_alive():
                raise ValueError("Stop the active sprint and wait before selecting previous evidence")
            directory, state = self._saved(identifier)
            if state["status"] not in TERMINAL:
                raise ValueError("Cannot select another active sprint")
            self.directory, self.state = directory, state
            return self.snapshot()

    def artifact(self, relative):
        with self.lock:
            owners = {path: role for role, spec in ROLES.items() for path in spec["paths"]}
            entry = next((a for a in self.state["artifacts"] if a.get("path") == relative), None)
            if not self.directory or not entry or relative not in owners or entry.get("owner") != owners[relative]:
                raise ValueError("Artifact not in its owner's manifest")
            if (self.directory / "artifacts").is_symlink():
                raise ValueError("Symlink artifact root rejected")
            target = safe_path(self.directory, "artifacts/" + relative)
            if target.stat().st_size > MAX_FILE_BYTES:
                raise ValueError("Artifact exceeds size limit")
            data = target.read_bytes()
            if len(data) != entry.get("bytes") or hashlib.sha256(data).hexdigest() != entry.get("sha256"):
                raise ValueError("Artifact integrity mismatch")
            return {"path": relative, "content": data.decode("utf-8"), "sha256": entry["sha256"]}

    def _check_approval(self):
        if canonical_hash(self.state["brief"]) != self.state["brief_hash"]:
            raise ValueError("Frozen brief changed")
        if json.loads(safe_path(self.directory, "brief.json").read_text()) != self.state["brief"]:
            raise ValueError("Saved brief changed")
        actual = self.artifact("decisions/build-memo.md")["sha256"]
        if self.state.get("approved_brief_hash") != self.state["brief_hash"] or self.state.get("approved_memo_hash") != actual:
            raise ValueError("Build approval no longer matches exact brief and memo")

    def export(self):
        with self.lock:
            if self.state["status"] not in ("packaged", "needs_fixes") or not self.directory:
                raise ValueError("Pack is not ready")
            self._check_approval()
            for entry in self.state["artifacts"]:
                self.artifact(entry["path"])
            from .readiness import verify_pack
            path = safe_path(self.directory, "submission-pack.zip")
            if path.stat().st_size > 15_000_000:
                raise ValueError("Pack exceeds export size limit")
            try:
                verified = verify_pack(path)
            except zipfile.BadZipFile as exc:
                raise ValueError("Export archive is corrupt") from exc
            if not verified.get("integrity_passed"):
                raise ValueError("Export pack integrity mismatch")
            return path.read_bytes()

    def snapshot(self) -> dict:
        with self.lock:
            return copy.deepcopy(self.state)

    def event(self, kind: str, **payload):
        with self.lock:
            event = {"seq": len(self.state["events"]) + 1, "at": utcnow(), "kind": kind, **payload}
            self.state["events"].append(event)
            if self.directory:
                with (self.directory / "events.jsonl").open("a", encoding="utf-8") as out:
                    out.write(json.dumps(event, ensure_ascii=False) + "\n")
                atomic_json(self.directory / "state.json", self.state)
            return event

    def start(self, brief: dict) -> dict:
        brief = validate_brief(brief)
        with self.lock:
            if self.thread and self.thread.is_alive():
                raise ValueError("A sprint is already active. Finish or stop it before creating another.")
            self.cancelled.clear(); self.paused.clear(); self.approval.clear()
            if hasattr(self.provider, "begin_run"):
                self.provider.begin_run()
            identifier = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
            self.directory = self.root / identifier
            (self.directory / "artifacts").mkdir(parents=True)
            self.state = {"id": identifier, "status": "discovery", "provider": self.provider.name,
                "brief": brief, "brief_hash": canonical_hash(brief), "created_at": utcnow(),
                "jobs": {r: {"name": v["name"], "phase": v["phase"], "status": "queued"} for r, v in ROLES.items()},
                "events": [], "artifacts": [], "usage": {"input_tokens": 0, "output_tokens": 0, "requests": 0},
                "calls_started": 0, "max_calls": self.max_calls, "concurrency_limit": self.concurrency,
                "limitations": ["No blockchain connection", "No automatic public publishing", "Local spend estimates are not provider billing guarantees", "No shell execution of generated code"]}
            atomic_json(self.directory / "brief.json", brief)
            self.event("sprint.started", message=f"{self.provider.name}: fixed sprint graph started")
            self.thread = threading.Thread(target=self._thread_main, daemon=True)
            self.thread.start()
            return self.snapshot()

    def approve(self, brief_hash: str, memo_hash: str | None = None):
        with self.lock:
            if self.state["status"] != "awaiting_approval" or brief_hash != self.state["brief_hash"]:
                raise ValueError("Approval is not valid for this state/brief")
            if canonical_hash(self.state["brief"]) != brief_hash or json.loads(safe_path(self.directory, "brief.json").read_text()) != self.state["brief"]:
                raise ValueError("Frozen brief changed; approval rejected")
            actual_hash = self.artifact("decisions/build-memo.md")["sha256"]
            if actual_hash != self.state.get("memo_hash"):
                raise ValueError("Build memo changed after review; approval rejected")
            if memo_hash != actual_hash:
                raise ValueError("Approval refers to a different build memo")
            self.state["approved_brief_hash"] = brief_hash
            self.state["approved_memo_hash"] = actual_hash
            self.event("founder.approved", brief_hash=brief_hash, memo_hash=actual_hash)
            self.approval.set()

    def pause(self):
        with self.lock:
            if not (self.thread and self.thread.is_alive()) or self.state["status"] in TERMINAL:
                raise ValueError("No active sprint")
            self.paused.set()
            self.state["paused"] = True
            self.event("sprint.pause_requested", message="Active calls may finish; new work is held.")

    def resume(self):
        with self.lock:
            if not (self.thread and self.thread.is_alive()) or self.state["status"] in TERMINAL:
                raise ValueError("No active sprint; interrupted runs cannot automatically resume paid calls")
            self.paused.clear(); self.state["paused"] = False
            self.event("sprint.resumed", message="New tasks may start.")

    def stop(self):
        with self.lock:
            if self.state["status"] in TERMINAL:
                return
            if not (self.thread and self.thread.is_alive()):
                raise ValueError("No active sprint")
            self.cancelled.set()
            self.state["status"] = "stopping"
            self.event("sprint.stop_requested", message="Cancel local tasks. Provider may bill already-started work.")

    async def _pause_point(self):
        while self.paused.is_set():
            if self.cancelled.is_set():
                raise asyncio.CancelledError()
            await asyncio.sleep(0.1)

    def _context_packet(self, role: str) -> tuple[str, dict]:
        # Only the capability's named inputs enter a role's frozen context.
        from .capabilities import profile_for
        profile = profile_for(role)
        snapshot = self.snapshot()
        inventory = {item['path']: item for item in snapshot['artifacts']}
        chunks, size = [], 0
        inputs = []
        for path in profile['input_paths']:
            if path not in inventory:
                raise ValueError('Required role input has not been accepted: ' + path)
            item = inventory[path]
            text = self.artifact(item["path"])["content"]
            if hashlib.sha256(text.encode()).hexdigest() != item["sha256"]:
                raise ValueError("Accepted artifact was modified outside its owner")
            size += len(text.encode())
            if size > 190000:
                raise ValueError("Context too large; narrow scope rather than silently dropping evidence")
            chunks.append(f"FILE {item['path']}\n{text}")
            inputs.append(copy.deepcopy(item))
        verification_hash = None
        if role == "reviewer":
            verification_hash = canonical_hash(snapshot.get('verification', {}))
            chunks.append("DETERMINISTIC VERIFICATION (not browser/chain proof):\n" +
                          json.dumps(snapshot.get("verification", {})))
        context = '\n\n'.join(chunks)
        mode = ('scripted-rehearsal' if self.provider.name == 'rehearsal' else
                'live-provider' if self.provider.name == 'openai-responses' else
                'contract-test' if self.provider.name == 'contract-test-responses' else 'unverified-provider')
        receipt = {'kind': 'prepared-role-context', 'version': 1, 'mode': mode,
                   'role': role, 'provider': self.provider.name, 'model': getattr(self.provider, 'model', None),
                   'profile': profile, 'profile_hash': canonical_hash(profile),
                   'brief_hash': snapshot['brief_hash'], 'context_sha256': hashlib.sha256(context.encode()).hexdigest(),
                   'input_artifacts': inputs, 'verification_sha256': verification_hash, 'tools': []}
        return context, receipt

    def _context(self, role: str) -> str:
        return self._context_packet(role)[0]

    def _record_usage(self, role: str, usage: dict):
        with self.lock:
            if self.state["jobs"][role].get("usage_recorded"):
                return
            self.state["jobs"][role]["usage"] = usage
            self.state["jobs"][role]["usage_recorded"] = True
            for key in ("input_tokens", "output_tokens", "requests"):
                self.state["usage"][key] += int(usage.get(key, 0))
            if hasattr(self.provider, "ledger"):
                self.state["spend"] = self.provider.ledger.snapshot()
            self.event("provider.usage_recorded", role=role, usage=usage)

    async def _job(self, role: str, semaphore: asyncio.Semaphore, context: str, receipt: dict):
        async with semaphore:
            await self._pause_point()
            with self.lock:
                if self.cancelled.is_set():
                    raise asyncio.CancelledError()
                if self.state["calls_started"] >= self.max_calls:
                    raise RuntimeError("Call limit reached; no additional work authorized")
                self.state["calls_started"] += 1
                self.state["jobs"][role].update(status="running", started_at=utcnow(), capability_receipt=receipt)
                self.event("job.started", role=role)
            started = time.monotonic()
            try:
                raw, usage = await asyncio.wait_for(self.provider.run(role, copy.deepcopy(self.state["brief"]), context), timeout=self.timeout)
                self._record_usage(role, usage)
                from .capabilities import validate_role_output
                quality = validate_role_output(role, raw, self.state['brief'])
                with self.lock:
                    self.state['jobs'][role]['quality_report'] = quality
                    self.event('job.output_checked', role=role, passed=quality['passed'],
                               check_ids=[c['id'] for c in quality['checks']])
                if not quality['passed']:
                    failed = [c['id'] for c in quality['checks'] if not c['passed']]
                    raise ValueError('Role output rejected: ' + ', '.join(failed))
                instruction_receipt = usage.get('instruction_receipt')
                if instruction_receipt and instruction_receipt.get('profile_hash') != receipt['profile_hash']:
                    raise ValueError('Prepared capability changed before the provider request')
                result = validate_result(role, raw)
                if self.cancelled.is_set():
                    raise asyncio.CancelledError()
                written = []
                # All results validated before any artifact becomes visible.
                staged = safe_path(self.directory, "staging/" + role)
                staged.mkdir(parents=True, exist_ok=True)
                for artifact in result["artifacts"]:
                    temporary = safe_path(staged, artifact["path"])
                    temporary.parent.mkdir(parents=True, exist_ok=True)
                    temporary.write_text(artifact["content"], encoding="utf-8")
                with self.lock:
                    if self.cancelled.is_set():
                        raise asyncio.CancelledError()
                    for artifact in result["artifacts"]:
                        path = artifact["path"]
                        target = safe_path(self.directory, "artifacts/" + path)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        safe_path(staged, path).replace(target)
                        entry = {"path": path, "owner": role, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "bytes": target.stat().st_size}
                        self.state["artifacts"].append(entry); written.append(entry)
                    self.state["jobs"][role].update(status="done", ended_at=utcnow(), duration_seconds=round(time.monotonic()-started, 3),
                        summary=result["summary"], limitations=result["limitations"], usage=usage)
                    self.event("job.completed", role=role, files=[x["path"] for x in written], usage=usage)
            except asyncio.CancelledError:
                with self.lock:
                    self.state["jobs"][role].update(status="cancelled", ended_at=utcnow())
                    self.event("job.cancelled", role=role)
                raise
            except Exception as exc:
                if getattr(exc, "usage", None):
                    self._record_usage(role, exc.usage)
                with self.lock:
                    if hasattr(self.provider, "ledger"):
                        self.state["spend"] = self.provider.ledger.snapshot()
                    # Do not display full provider errors: they can contain sensitive input.
                    detail = str(exc)[:240] if self.provider.name == "rehearsal" else f"{type(exc).__name__}; inspect provider/account settings locally. No retry was made."
                    self.state["jobs"][role].update(status="failed", ended_at=utcnow(), error=detail)
                    self.event("job.failed", role=role, message=detail)
                raise

    async def _wave(self, roles: list[str]):
        semaphore = asyncio.Semaphore(self.concurrency)
        packets = {role: self._context_packet(role) for role in roles}
        async with asyncio.TaskGroup() as group:
            for role in roles:
                group.create_task(self._job(role, semaphore, *packets[role]))

    async def _pipeline(self):
        await self._wave(["research", "product", "architect"])
        await self._wave(["chief"])
        with self.lock:
            self.state["status"] = "awaiting_approval"
            self.state["memo_hash"] = hashlib.sha256((self.directory / "artifacts/decisions/build-memo.md").read_bytes()).hexdigest()
            self.event("founder.approval_required", memo_hash=self.state["memo_hash"], brief_hash=self.state["brief_hash"], artifact="decisions/build-memo.md")
        while not self.approval.is_set():
            await asyncio.sleep(0.1)
        await self._pause_point()
        with self.lock:
            self._check_approval()
            self.state["status"] = "building"
            self.event("build.started", message="Three disjoint output contracts, no shared-file editing.")
        await self._wave(["frontend", "domain", "submission"])
        with self.lock:
            self.state["status"] = "verifying"
            report = verify_artifacts(self.directory / "artifacts")
            report['role_outputs'] = {role: copy.deepcopy(job['quality_report'])
                for role, job in self.state['jobs'].items() if 'quality_report' in job}
            report['passed'] = report['passed'] and all(item['passed'] for item in report['role_outputs'].values())
            self.state["verification"] = report
            atomic_json(self.directory / "verification.json", report)
            self.event("verification.completed", passed=report["passed"], check_type="static-contract-checks")
        await self._wave(["reviewer"])
        with self.lock:
            self.state["status"] = "packaged" if report["passed"] else "needs_fixes"
            self.state["ended_at"] = utcnow()
            self.event("sprint.finished", message="Draft pack generated; not submitted, deployed or chain-verified.")
            self._package()

    async def _run(self):
        task = asyncio.create_task(self._pipeline())
        started = time.monotonic()
        try:
            while not task.done():
                await asyncio.sleep(0.08)
                if self.cancelled.is_set() or time.monotonic()-started > self.max_elapsed:
                    task.cancel()
                    break
            await task
        except asyncio.CancelledError:
            with self.lock:
                self.state["status"] = "stopped"
                self.event("sprint.stopped", message="No new work; in-flight provider costs may still apply.")
        except Exception:
            with self.lock:
                self.state["status"] = "failed"
                self.event("sprint.failed", message="A task failed. No automatic retries or permission expansion.")
        finally:
            if hasattr(self.provider, "close"):
                await self.provider.close()
                self.provider._client = None

    def _thread_main(self):
        asyncio.run(self._run())

    def _package(self):
        self._check_approval()
        for entry in self.state["artifacts"]:
            self.artifact(entry["path"])
        manifest = {"run_id": self.state["id"], "provider": self.state["provider"],
                    "brief_hash": self.state["brief_hash"], "artifacts": self.state["artifacts"],
                    "status": "draft-not-submitted", "chain_verified": False}
        from .readiness import evaluate_run
        readiness = evaluate_run(self.state)
        atomic_json(self.directory / "readiness.json", readiness)
        manifest["approved_memo_hash"] = self.state.get("approved_memo_hash")
        manifest['capability_evidence_hash'] = canonical_hash({role: {
            'capability_receipt': job.get('capability_receipt'), 'quality_report': job.get('quality_report'),
            'instruction_receipt': job.get('usage', {}).get('instruction_receipt'),
        } for role, job in self.state['jobs'].items()})
        atomic_json(self.directory / "manifest.json", manifest)
        temporary = self.directory / "submission-pack.zip.tmp"
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as z:
            for name in ("brief.json", "state.json", "events.jsonl", "verification.json", "manifest.json", "readiness.json"):
                z.write(self.directory / name, name)
            for entry in self.state["artifacts"]:
                z.write(safe_path(self.directory, "artifacts/" + entry["path"]), "artifacts/" + entry["path"])

        from .readiness import verify_pack
        if not verify_pack(temporary)["integrity_passed"]:
            raise ValueError("Generated ZIP failed integrity verification")
        temporary.replace(self.directory / "submission-pack.zip")
