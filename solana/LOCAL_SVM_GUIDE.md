# Reproduce the compiled local Solana demo

This guide reproduces the recorded SBPFv3 build and isolated LiteSVM execution. It does not deploy, connect a wallet, request public funds or send a network transaction. Run every command from the PredictKit source root unless a subshell explicitly changes directory.

## 1. Install the pinned Node test dependencies

Node 20 or newer is required; verification used Node 22.22.2.

```bash
(cd solana/client && npm ci --ignore-scripts)
```

This installs `@solana/web3.js` 1.98.4 and the development-only LiteSVM 1.5.0 native package from the lockfile. Lifecycle scripts are disabled. The recorded audit reports four moderate transitive advisories through the web3.js dependency tree, with no high or critical findings. Do not use this result as a production dependency/security approval, and do not apply `npm audit fix --force`: its proposed web3.js downgrade is not a compatible remediation.

## 2. Obtain and verify the official SBF compiler

The successful machine was macOS x86_64. The official [Anza platform-tools 1.57 release](https://github.com/anza-xyz/platform-tools/releases/tag/v1.57) supplies the SBF Rust compiler, Cargo and LLVM. It is separate from the host Rust toolchain. Select the matching architecture archive for another machine; do not reuse the Mac checksum for a different archive.

For the verified macOS x86_64 archive:

- Asset: `platform-tools-osx-x86_64.tar.bz2`
- Size: `441084457` bytes
- SHA256: `e6f6231b149e64ad6cc12605d0f993405ce55862aa44406c023563159f8c3caf`
- Official URL: [download this archive](https://github.com/anza-xyz/platform-tools/releases/download/v1.57/platform-tools-osx-x86_64.tar.bz2)

```bash
mkdir -p solana/.tools/downloads solana/.tools/platform-tools-v1.57
curl --fail --location --retry 3 --continue-at - \
  https://github.com/anza-xyz/platform-tools/releases/download/v1.57/platform-tools-osx-x86_64.tar.bz2 \
  --output solana/.tools/downloads/platform-tools-complete.tar.bz2
```

Verify the whole archive and extract with path filtering before executing any binary (Python 3.12+):

```bash
python3 - <<'PY'
from pathlib import Path
import hashlib, tarfile
archive = Path('solana/.tools/downloads/platform-tools-complete.tar.bz2')
assert archive.stat().st_size == 441084457
assert hashlib.sha256(archive.read_bytes()).hexdigest() == 'e6f6231b149e64ad6cc12605d0f993405ce55862aa44406c023563159f8c3caf'
with tarfile.open(archive, 'r:bz2') as source:
    source.extractall('solana/.tools/platform-tools-v1.57', filter='data')
PY
```

The original single-connection download stalled; the recorded run recovered through bounded range requests and verified the combined archive against the same official digest. That recovery changes transport only, not the artifact being executed.

## 3. Populate the locked target cache, then build offline

The host-test cache alone lacked `solana-define-syscall` 5.2.0. Fetching the existing lockfile for the SBF target resolved that cache miss without changing dependencies:

```bash
CARGO_HOME="$PWD/.local/cargo-home" \
RUSTC="$PWD/solana/.tools/platform-tools-v1.57/rust/bin/rustc" \
solana/.tools/platform-tools-v1.57/rust/bin/cargo fetch \
  --locked --target sbpfv3-solana-solana --manifest-path solana/Cargo.toml

python3 solana/scripts/build-sbf-local.py \
  --platform-tools solana/.tools/platform-tools-v1.57 \
  --cargo-home .local/cargo-home \
  --evidence evidence/my-sbf-build
```

The script uses the official bundled compiler directly, following the [cargo-build-sbf SBPFv3 invocation](https://github.com/anza-xyz/cargo-build-sbf). It preserves the user's `HOME` and rustup configuration. It explicitly sets the project target directory, builds `--offline --locked --release --target sbpfv3-solana-solana`, and rejects output without SBPFv3 ELF flags. It records compiler version, command, exit code, byte count and SHA256. No program keypair is generated or loaded.

Default output: `solana/target/sbpfv3-solana-solana/release/predictkit_registry.so`. Tests can use a different explicitly selected build via `PREDICTKIT_SBF_PATH`, but they still require an ELF and record its hash. Missing output is an error, never a skip.

The build emits six Anchor macro `unexpected_cfgs` warnings, retained in evidence. They did not block compilation or the SVM tests; no warnings were hidden by globally changing compiler settings.

## 4. Execute the program and inspect the demo

```bash
node --test solana/tests/codec.test.mjs solana/tests/client.test.mjs solana/tests/svm.test.mjs
node solana/scripts/run-local-demo.mjs evidence/my-local-demo.json
```

The demo connects the real SDK instruction builders to the compiled registry inside LiteSVM:

1. Create the question with an authority, designated resolver, rules hash and closing schedule.
2. Record separate 6800 and 4200 basis-point forecasts.
3. Move the test clock to close and assert that a new forecast is rejected.
4. Move the clock to the permitted resolution time and resolve YES using the designated test resolver.
5. Decode the stored final account and confirm the count remains two.

The JSON records every operation's success/rejection, actual VM logs, compute units, local signature, account IDs and program hash. Secrets are never serialized. Keys, balances, signatures and manipulated time belong to this in-process test only. There is no RPC endpoint or public deployment behind them.

The evidence proves program execution under these tests. It does not establish real-wallet UX, devnet/mainnet deployment, RPC behavior under load, an independent oracle, economic soundness or production security. See [TEST_PLAN.md](TEST_PLAN.md) for covered cases and remaining gates.
