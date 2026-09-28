"""Evidence-based release checks, never a model's self-reported readiness score."""
from __future__ import annotations
import hashlib
import json
import re
import stat
from datetime import datetime
from pathlib import Path, PurePosixPath
import zipfile


def evaluate_run(state: dict) -> dict:
    jobs = state.get('jobs', {})
    if not isinstance(jobs, dict) or not all(isinstance(j, dict) for j in jobs.values()):
        raise ValueError('Invalid job evidence')
    real = state.get('provider') in ('openai-responses', 'openai-agents')
    from .contracts import ROLES
    identifiers = []
    observed = real and set(jobs) == set(ROLES)
    for job in jobs.values():
        usage = job.get('usage', {})
        if not isinstance(usage, dict):
            raise ValueError('Invalid usage evidence')
        ids = usage.get('response_ids', [])
        valid_ids = (isinstance(ids, list) and len(ids) == 1 and
                     isinstance(ids[0], str) and bool(ids[0].strip()))
        observed = observed and job.get('status') == 'done' and valid_ids and (
            usage.get('provider') == state.get('provider') and usage.get('requests') == 1 and
            all(type(usage.get(k)) is int and usage[k] >= 0 for k in ('input_tokens', 'output_tokens')))
        if valid_ids:
            identifiers.extend(ids)
    observed = observed and len(identifiers) == 8 and len(set(identifiers)) == 8
    overlap = False
    try:
        starts = [datetime.fromisoformat(jobs[r]['started_at']) for r in ('research', 'product', 'architect')]
        ends = [datetime.fromisoformat(jobs[r]['ended_at']) for r in ('research', 'product', 'architect')]
        overlap = max(starts) < min(ends)
    except (ValueError, KeyError, TypeError):
        pass
    checks = [
        {'id': 'files', 'label': 'Static artifact contracts', 'passed': bool(state.get('verification', {}).get('passed'))},
        {'id': 'approval', 'label': 'Founder approved exact brief and memo',
         'passed': bool(state.get('memo_hash') and state.get('brief_hash') and
                        state.get('approved_memo_hash') == state.get('memo_hash') and
                        state.get('approved_brief_hash') == state.get('brief_hash'))},
        {'id': 'models', 'label': 'All eight roles have provider response IDs and usage', 'passed': bool(observed)},
        {'id': 'parallel', 'label': 'Discovery task intervals overlap', 'passed': overlap},
        {'id': 'generated-browser', 'label': 'Generated live app browser tested', 'passed': False},
        {'id': 'chain', 'label': 'Meaningful Solana flow independently verified', 'passed': False},
        {'id': 'builders', 'label': 'Three independent builder rehearsals', 'passed': False},
    ]
    return {'kind': 'local-evidence-checklist', 'provider': state.get('provider'), 'checks': checks,
            'workshop_ready': all(c['passed'] for c in checks),
            'note': 'Task overlap is not proof of model execution. Chain/browser/user proof cannot be self-asserted by a generated file.'}


def verify_pack(path: Path) -> dict:
    """Check the entire declared pack, without extraction or code execution.

    Local cross-checks cannot attest who produced this archive. Unsupported
    readiness claims are rejected, even if an artifact's hash is consistent.
    """
    from .contracts import ROLES, canonical_hash
    required = {'brief.json', 'state.json', 'events.jsonl', 'verification.json', 'manifest.json', 'readiness.json'}
    owners = {p: role for role, spec in ROLES.items() for p in spec['paths']}
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or len(names) > 1000:
            raise ValueError('Duplicate names or too many ZIP entries')
        if any(PurePosixPath(n).is_absolute() or any(p in ('', '.', '..') for p in n.split('/'))
               or '\\' in n or '\x00' in n or ':' in n for n in names):
            raise ValueError('Unsafe ZIP path')
        if any(stat.S_ISLNK(i.external_attr >> 16) or i.flag_bits & 1 for i in z.infolist()):
            raise ValueError('Symlink or encrypted ZIP entry rejected')
        if sum(i.file_size for i in z.infolist()) > 15_000_000:
            raise ValueError('Uncompressed ZIP exceeds verification limit')
        if not required.issubset(names):
            raise ValueError('Incomplete pack metadata')
        try:
            manifest = json.loads(z.read('manifest.json'))
            state = json.loads(z.read('state.json'))
            brief = json.loads(z.read('brief.json'))
            verification = json.loads(z.read('verification.json'))
            readiness = json.loads(z.read('readiness.json'))
        except (ValueError, UnicodeError) as exc:
            raise ValueError('Invalid pack metadata JSON') from exc
        if not all(isinstance(x, dict) for x in (manifest, state, brief, verification, readiness)):
            raise ValueError('Pack metadata must be JSON objects')
        entries = manifest.get('artifacts')
        if not isinstance(entries, list) or len(entries) != len(owners):
            raise ValueError('Manifest must contain the complete role artifact inventory')
        seen = set()
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError('Invalid manifest artifact')
            relative = entry.get('path')
            if not isinstance(relative, str) or relative not in owners or relative in seen:
                raise ValueError('Unknown or duplicate manifest artifact')
            if (entry.get('owner') != owners[relative] or
                not isinstance(entry.get('sha256'), str) or
                not re.fullmatch('[0-9a-f]{64}', entry['sha256']) or
                type(entry.get('bytes')) is not int or entry['bytes'] <= 0):
                raise ValueError('Invalid artifact ownership, hash or size')
            seen.add(relative)
        expected = required | {'artifacts/' + p for p in seen}
        if set(names) != expected:
            raise ValueError('Archive contents do not match the complete manifest')
        bad = []
        for entry in entries:
            data = z.read('artifacts/' + entry['path'])
            if hashlib.sha256(data).hexdigest() != entry['sha256'] or len(data) != entry['bytes']:
                bad.append(entry['path'])
        if canonical_hash(brief) != manifest.get('brief_hash'):
            bad.append('brief.json')
        if (state.get('brief') != brief or state.get('brief_hash') != manifest.get('brief_hash') or
            state.get('id') != manifest.get('run_id') or state.get('provider') != manifest.get('provider') or
            state.get('artifacts') != entries or state.get('verification') != verification or
            state.get('approved_memo_hash') != manifest.get('approved_memo_hash')):
            bad.append('state.json')
        memo_hash = hashlib.sha256(z.read('artifacts/decisions/build-memo.md')).hexdigest()
        if (state.get('memo_hash') != memo_hash or state.get('approved_memo_hash') != memo_hash or
            state.get('approved_brief_hash') != state.get('brief_hash')):
            bad.append('approval')
        if readiness != evaluate_run(state) or manifest.get('chain_verified') is not False:
            bad.append('readiness.json')
        # New packs bind their recorded capabilities and checks. Legacy packs
        # retain their original verification path and never gain invented receipts.
        jobs = state.get('jobs', {})
        has_role_evidence = ('role_outputs' in verification or any(
            'capability_receipt' in job or 'quality_report' in job or
            'instruction_receipt' in job.get('usage', {}) for job in jobs.values()))
        if has_role_evidence and 'capability_evidence_hash' not in manifest:
            bad.append('capability-evidence')
        if 'capability_evidence_hash' in manifest:
            evidence = {role: {
                'capability_receipt': job.get('capability_receipt'),
                'quality_report': job.get('quality_report'),
                'instruction_receipt': job.get('usage', {}).get('instruction_receipt'),
            } for role, job in jobs.items()}
            if canonical_hash(evidence) != manifest['capability_evidence_hash']:
                bad.append('capability-evidence')
            try:
                from .capabilities import profile_for
                expected_mode = ('scripted-rehearsal' if state['provider'] == 'rehearsal' else
                    'live-provider' if state['provider'] == 'openai-responses' else
                    'contract-test' if state['provider'] == 'contract-test-responses' else 'unverified-provider')
                for role in ROLES:
                    job = jobs[role]
                    receipt, report = job['capability_receipt'], job['quality_report']
                    profile = receipt['profile']
                    expected_profile = profile_for(role)
                    expected_checks = [(c['id'], c['label']) for c in profile['acceptance_checks']]
                    actual_checks = [(c['id'], c['label']) for c in report['checks']]
                    if (receipt['kind'] != 'prepared-role-context' or type(receipt['version']) is not int or receipt['version'] != 1 or
                        receipt['provider'] != state['provider'] or receipt['mode'] != expected_mode or
                        receipt['provider'] != job['usage']['provider'] or receipt['model'] != job['usage'].get('model') or
                        job['status'] != 'done' or profile['id'] != role or
                        profile['version'] != expected_profile['version'] or report['version'] != profile['version'] or
                        report['kind'] != 'role-output-checks' or
                        profile['input_paths'] != expected_profile['input_paths'] or
                        profile['skill_ids'] != expected_profile['skill_ids'] or
                        [c['id'] for c in profile['acceptance_checks']] != [c['id'] for c in expected_profile['acceptance_checks']] or
                        actual_checks != expected_checks or
                        receipt['role'] != role or receipt['brief_hash'] != manifest['brief_hash'] or
                        canonical_hash(profile) != receipt['profile_hash'] or receipt['tools'] != [] or
                        profile['output_paths'] != ROLES[role]['paths'] or report['passed'] is not True or
                        not report['checks'] or not all(c['passed'] is True for c in report['checks'])):
                        raise ValueError('Inconsistent role evidence')
                    if role != 'reviewer' and report != verification['role_outputs'][role]:
                        raise ValueError('Verification and role check reports disagree')
                    supplied = receipt['input_artifacts']
                    if [entry['path'] for entry in supplied] != profile['input_paths']:
                        raise ValueError('Inconsistent role inputs')
                    chunks = []
                    for entry in supplied:
                        if entry not in entries:
                            raise ValueError('Role input not in accepted manifest')
                        content = z.read('artifacts/' + entry['path']).decode('utf-8')
                        chunks.append(f"FILE {entry['path']}\n{content}")
                    if role == 'reviewer':
                        if receipt['verification_sha256'] != canonical_hash(verification):
                            raise ValueError('Reviewer verification evidence changed')
                        chunks.append('DETERMINISTIC VERIFICATION (not browser/chain proof):\n' + json.dumps(verification))
                    if receipt['context_sha256'] != hashlib.sha256('\n\n'.join(chunks).encode()).hexdigest():
                        raise ValueError('Role context hash changed')
                    instruction = job.get('usage', {}).get('instruction_receipt')
                    if state['provider'] in ('openai-responses', 'contract-test-responses') and not instruction:
                        raise ValueError('Provider instruction receipt missing')
                    if expected_mode == 'scripted-rehearsal' and instruction:
                        raise ValueError('Rehearsal does not execute role instructions')
                    if instruction:
                        if (instruction['kind'] != 'assembled-role-request' or instruction['version'] != 1 or
                            instruction['role'] != role or instruction['profile_hash'] != receipt['profile_hash'] or
                            instruction['role_prompt']['path'] != f'agents/{role}.md' or
                            instruction['common']['path'] != 'AGENTS.md' or
                            [r['path'] for r in instruction['project_context']] != ['PROJECT.md', 'SOUL.md', 'docs/IMPLEMENTATION_STATUS.md'] or
                            [s['path'] for s in instruction['skills']] != [f'skills/{s}/SKILL.md' for s in profile['skill_ids']]):
                            raise ValueError('Provider capability mismatch')
                        hashes = [instruction[k] for k in ('instructions_sha256', 'input_sha256', 'schema_sha256')]
                        hashes += [r['sha256'] for r in [instruction['common'], instruction['role_prompt'], *instruction['skills'], *instruction['project_context']]]
                        if role == 'frontend':
                            if instruction['reference_app']['path'] != 'templates/reference-app.html':
                                raise ValueError('Frontend reference receipt missing')
                            hashes.append(instruction['reference_app']['rendered_sha256'])
                        if not all(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) for value in hashes):
                            raise ValueError('Invalid instruction hash')
            except (KeyError, TypeError, ValueError, UnicodeError):
                bad.append('role-receipts')
        try:
            events = [json.loads(line) for line in z.read('events.jsonl').decode().splitlines() if line.strip()]
            if events != state.get('events'):
                bad.append('events.jsonl')
        except (ValueError, UnicodeError):
            bad.append('events.jsonl')
        return {'integrity_passed': not bad, 'mismatches': bad, 'artifacts_checked': len(entries),
                'boundary': 'Internal consistency only, not authenticity, security, provider or chain verification',
                'readiness': evaluate_run(state)}
