"""Local-only prerequisites. Never read key values or contact an account."""
import importlib.metadata
import os
import shutil
import sys
from .skills import ROLE_SKILLS, load_skills


def sdk_distribution_version():
    try:
        return importlib.metadata.version('openai-agents')
    except importlib.metadata.PackageNotFoundError:
        return None


def environment_report():
    from .spend import SpendPolicy
    try:
        policy = SpendPolicy.from_env(os.environ).view()
        policy_error = None
    except ValueError as exc:
        policy, policy_error = None, str(exc)
    key_present = bool(os.environ.get('OPENAI_API_KEY'))
    model_present = bool(os.environ.get('PREDICTKIT_MODEL'))
    version = sdk_distribution_version()
    return {'version': '0.2.0', 'python': sys.version.split()[0], 'rehearsal_ready': True,
            'live_transport': 'stdlib-https-responses', 'live_transport_needs_package_install': False,
            'agents_sdk_installed': version is not None, 'optional_legacy_sdk_version': version,
            'api_key_present': key_present, 'model_configured': model_present,
            'spend_policy': policy, 'spend_policy_error': policy_error,
            'live_prerequisites_present': key_present and model_present and policy is not None,
            'live_provider_verified': False, 'chain_integrated': False,
            'rust_compiler_available': bool(shutil.which('rustc')), 'anchor_available': bool(shutil.which('anchor')),
            'solana_cli_available': bool(shutil.which('solana')), 'node_available': bool(shutil.which('node')),
            'reviewed_skills': {r: load_skills(r)[1] for r in ROLE_SKILLS},
            'boundary': 'Presence checks only. No paid calls, network tests, deployments or wallet operations.'}
