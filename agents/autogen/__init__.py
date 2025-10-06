"""
AutoGen integration for the KindRoot agent system.
This package exposes agent utilities and services.
"""

__all__ = [
    'OpenAIChat',
    'TriageService',
    'PatientParseService',
    'LeadInvestigatorService',
    'TriageResult',
    'PatientParse',
    'InvestigatorOutput',
    'AutoGenAdapter',
]

try:
    from .agents import (
        OpenAIChat,
        TriageService,
        PatientParseService,
        LeadInvestigatorService,
        TriageResult,
        PatientParse,
        InvestigatorOutput,
        AutoGenAdapter,
    )
except Exception as e:
    # If imports fail, expose nothing
    __all__ = []
    import warnings
    warnings.warn(f"Failed to import agents module: {e}")
