"""Conservative local spend reservations. Not a provider billing hard limit."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import date
import threading


def positive(value, field):
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f'Invalid {field}') from exc
    if not amount.is_finite() or amount <= 0:
        raise ValueError(f'{field} must be a finite positive number')
    return amount

@dataclass(frozen=True)
class SpendPolicy:
    budget_usd: Decimal
    input_per_million: Decimal
    output_per_million: Decimal
    price_checked_on: str
    max_output_tokens: int = 8000

    @classmethod
    def from_env(cls, env):
        keys = ['PREDICTKIT_BUDGET_USD', 'PREDICTKIT_INPUT_USD_PER_MILLION',
                'PREDICTKIT_OUTPUT_USD_PER_MILLION', 'PREDICTKIT_PRICE_CHECKED_ON']
        if any(not env.get(k) for k in keys):
            raise ValueError('Live mode requires a budget, both token prices, and PREDICTKIT_PRICE_CHECKED_ON; see docs/LIVE_RUN.md')
        checked = date.fromisoformat(env[keys[3]])
        # Dates are explicit rather than making an assumed model price appear current.
        limit = int(env.get('PREDICTKIT_MAX_OUTPUT_TOKENS', '8000'))
        if not 1000 <= limit <= 16000:
            raise ValueError('Output-token limit must be 1000–16000')
        return cls(positive(env[keys[0]], 'budget'), positive(env[keys[1]], 'input price'),
                   positive(env[keys[2]], 'output price'), checked.isoformat(), limit)

    def view(self):
        return {'budget_usd': str(self.budget_usd), 'input_usd_per_million': str(self.input_per_million),
                'output_usd_per_million': str(self.output_per_million), 'price_checked_on': self.price_checked_on,
                'max_output_tokens': self.max_output_tokens,
                'boundary': 'Local estimates/reservations, not a guaranteed provider billing ceiling'}

class SpendLedger:
    def __init__(self, policy: SpendPolicy):
        self.policy, self.lock, self.entries = policy, threading.RLock(), {}

    def reserve(self, role, request_bytes):
        with self.lock:
            if role in self.entries:
                raise ValueError('Duplicate role dispatch rejected')
            # UTF-8 bytes + overhead deliberately overestimates ordinary text tokens.
            # Not a formal tokenizer or a provider billing guarantee.
            cost = ((Decimal(request_bytes + 4096) * self.policy.input_per_million +
                     Decimal(self.policy.max_output_tokens) * self.policy.output_per_million) / Decimal(1000000))
            held = sum((x['charged_or_held'] for x in self.entries.values()), Decimal(0))
            if held + cost > self.policy.budget_usd:
                raise ValueError('Local spend reservation would exceed the approved run budget')
            self.entries[role] = {'reserved': cost, 'charged_or_held': cost, 'status': 'reserved'}
            return str(cost)

    def reconcile(self, role, usage):
        with self.lock:
            cost = ((Decimal(usage['input_tokens']) * self.policy.input_per_million +
                     Decimal(usage['output_tokens']) * self.policy.output_per_million) / Decimal(1000000))
            entry = self.entries[role]
            entry.update(charged_or_held=cost, status='observed_usage', actual_estimated_usd=cost)
            # Cached input is deliberately charged at the uncached configured rate.
            entry['reservation_exceeded'] = cost > entry['reserved']
            return str(cost)

    def mark_uncertain(self, role):
        with self.lock:
            if role in self.entries and self.entries[role]['status'] != 'observed_usage':
                self.entries[role]['status'] = 'billing_unknown_reservation_retained'

    def snapshot(self):
        with self.lock:
            entries = {r: {k: str(v) if isinstance(v, Decimal) else v for k, v in e.items()}
                       for r, e in self.entries.items()}
            return {**self.policy.view(), 'entries': entries,
                    'charged_or_held_usd': str(sum((x['charged_or_held'] for x in self.entries.values()), Decimal(0)))}
