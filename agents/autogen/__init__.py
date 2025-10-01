"""
AutoGen integration for the KindRoot agent system.
This package exposes agent utilities. AutoGen dependencies are optional.
"""

__all__ = []

try:
    # Try to expose both when dependencies are present
    from .autogen_agent import AutoGenAgent, triage_safety  # type: ignore
    __all__ = ['AutoGenAgent', 'triage_safety']
except Exception:
    # Fallback: expose triage_safety if available without full AutoGen stack
    try:
        from .autogen_agent import triage_safety  # type: ignore
        __all__ = ['triage_safety']
    except Exception:
        # Nothing to export
        __all__ = []
