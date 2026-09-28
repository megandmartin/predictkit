"""Reviewed, role-scoped instruction loading; never remote skill execution."""
from pathlib import Path
import hashlib
from .contracts import ROLES, safe_path

ROOT = Path(__file__).resolve().parents[1]
ROLE_SKILLS = {
    'research': ['frame-opportunity', 'collect-evidence'],
    'product': ['frame-opportunity', 'specify-market'],
    'architect': ['select-solana-adapter', 'specify-market'],
    'chief': ['parallel-build'],
    'frontend': ['build-prediction-ui', 'parallel-build'],
    'domain': ['specify-market', 'verify-outcome'],
    'submission': ['prepare-submission', 'collect-evidence'],
    'reviewer': ['verify-outcome', 'collect-evidence'],
}

def read_instruction(relative: str, root: Path = ROOT) -> tuple[str, dict]:
    """Read a caller-allowlisted local instruction, including parent symlink checks."""
    root = Path(root)
    if root.is_symlink():
        raise ValueError('Instruction root must not be symlinked')
    path = safe_path(root, relative)
    if path.stat().st_size > 20000:
        raise ValueError('Instruction exceeds size limit')
    content = path.read_bytes()
    if len(content) > 20000:
        raise ValueError('Instruction exceeds size limit')
    text = content.decode('utf-8')
    if not text.strip():
        raise ValueError('Instruction is empty')
    return text, {'path': relative, 'sha256': hashlib.sha256(content).hexdigest()}

def load_skills(role: str, root: Path = ROOT) -> tuple[str, list[dict]]:
    texts, records = [], []
    for name in ROLE_SKILLS[role]:
        relative = f'skills/{name}/SKILL.md'
        content, record = read_instruction(relative, root)
        texts.append(f'REVIEWED SKILL: {name}\n{content}')
        records.append(record)
    return '\n\n'.join(texts), records

def load_role_instructions(role: str, root: Path = ROOT) -> tuple[str, dict]:
    if role not in ROLES:
        raise ValueError('Unknown instruction role')
    common, common_record = read_instruction('AGENTS.md', root)
    prompt, prompt_record = read_instruction(f'agents/{role}.md', root)
    skills, skill_records = load_skills(role, root)
    context_texts, context_records = [], []
    for relative in ('PROJECT.md', 'SOUL.md', 'docs/IMPLEMENTATION_STATUS.md'):
        text, record = read_instruction(relative, root)
        context_texts.append(f'PACKAGED PROJECT CONTEXT: {relative}\n{text}')
        context_records.append(record)
    return '\n\n'.join((common, *context_texts, prompt, skills)), {
        'common': common_record, 'role_prompt': prompt_record, 'skills': skill_records,
        'project_context': context_records,
    }
