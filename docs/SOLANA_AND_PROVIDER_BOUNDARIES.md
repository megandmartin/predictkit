# Provider and chain boundaries — v0.2

The agent runtime generates bounded files. It cannot initiate a chain action, hold a wallet key, browse for evidence or install arbitrary packages. Its model key remains in the local server process. Live requests go only to the fixed OpenAI Responses endpoint with normal TLS validation and redirects rejected.

The reference apps are off-chain simulations. They do not become on-chain because the repository now contains a Rust program. No generated app imports that client or knows a verified program deployment yet.

The proposed registry records questions, per-wallet forecasts and authorized YES/NO/VOID attestations. It has no collateral, trades, AMM, custody, oracle or payouts. One wallet is not one person; sybil resistance and forecasting quality are not solved. A resolver's signature and evidence hash do not prove the underlying event.

The candidate JavaScript client builds instructions, checks devnet genesis and account ownership, and requires per-transaction approval plus a wallet-signature interface. It has not been installed or integration-tested here. It does not load a private key. The read-only inspector is separate, uses no wallet and sends no transaction. Its fixture tests are not blockchain proof.

Before publication: review code, dependencies, actual licenses, deployed program/upgrade authority, rate/account policy, test evidence and the claims in the pitch. Do not enable real-money use or describe this source as audited.
