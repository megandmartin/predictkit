#!/usr/bin/env python3
"""Build with an explicitly selected official platform-tools directory.

This follows cargo-build-sbf's cargo invocation for SBPFv3 while avoiding its
HOME-based cache and rustup changes. It does not download, install or deploy.
The caller must first verify the official archive digest before extraction.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess

SOLANA = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--platform-tools', required=True, type=Path)
parser.add_argument('--cargo-home', required=True, type=Path)
parser.add_argument('--evidence', required=True, type=Path)
args = parser.parse_args()
platform = args.platform_tools.resolve()
evidence = args.evidence.resolve()
evidence.mkdir(parents=True, exist_ok=True)
compiler = platform / 'rust/bin/rustc'
cargo = platform / 'rust/bin/cargo'
for required in (compiler, cargo, platform / 'llvm/bin/clang', platform / 'llvm/bin/llvm-ar'):
    if not required.is_file():
        raise SystemExit(f'Missing required platform tool: {required}')
environment = os.environ.copy()
environment.update({
    'CARGO_HOME': str(args.cargo_home.resolve()),
    'CARGO_TARGET_DIR': str(SOLANA / 'target'),
    'RUSTC': str(compiler),
    'RUSTDOC': str(platform / 'rust/bin/rustdoc'),
    'CC': str(platform / 'llvm/bin/clang'),
    'AR': str(platform / 'llvm/bin/llvm-ar'),
    'CARGO_TARGET_SBPFV3_SOLANA_SOLANA_RUSTFLAGS': '-C link-arg=-z -C link-arg=defs -Zremap-cwd-prefix=',
})
environment.pop('RUSTFLAGS', None)
command = [str(cargo), 'build', '--offline', '--locked', '--release', '--target', 'sbpfv3-solana-solana', '--manifest-path', str(SOLANA / 'Cargo.toml')]
version = subprocess.run([str(compiler), '--version'], capture_output=True, text=True, check=True).stdout.strip()
with (evidence / 'sbf-build.log').open('w') as log:
    run = subprocess.run(command, cwd=SOLANA, env=environment, stdout=log, stderr=subprocess.STDOUT)
program = SOLANA / 'target/sbpfv3-solana-solana/release/predictkit_registry.so'
result = {'kind': 'local-sbf-build', 'architecture': 'SBPFv3', 'compiler': version, 'exit_code': run.returncode, 'command': command, 'used_network': False, 'deployed': False}
if run.returncode == 0:
    data = program.read_bytes()
    if data[:4] != b'\x7fELF' or len(data) < 64:
        raise SystemExit('Output is not an ELF program')
    flags = int.from_bytes(data[48:52], 'little')
    if flags != 3:
        raise SystemExit(f'Expected SBPFv3 ELF flags; got {flags}')
    result.update(program_path=str(program.relative_to(SOLANA)), bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), elf_flags=int.from_bytes(data[48:52], 'little'))
(evidence / 'sbf-build.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
raise SystemExit(run.returncode)
