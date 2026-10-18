"""Deprecated compatibility alias for the fail-closed canonical 35-gate evaluator.

Historically this module could assert release_ready=True on self-attested
pass flags. Importing it now delegates to the canonical evaluator, which
always requires an independent release authorization path.
"""
from .sudarshan_gates_35 import GATES, evaluate

__all__ = ("GATES", "evaluate")
