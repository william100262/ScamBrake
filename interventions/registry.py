"""Explicit strategy allowlist; never resolve user-controlled import paths."""
from types import MappingProxyType
from . import authority, diversion, questioning, social_influence

STRATEGIES = MappingProxyType({
    "questioning": questioning.build,
    "authority": authority.build,
    "social_influence": social_influence.build,
    "diversion": diversion.build,
})


def build_strategy(strategy: str, analysis: dict) -> dict:
    if not isinstance(strategy, str) or strategy not in STRATEGIES:
        raise ValueError("Unknown intervention strategy. Choose questioning, authority, social_influence, or diversion.")
    return STRATEGIES[strategy](analysis)
