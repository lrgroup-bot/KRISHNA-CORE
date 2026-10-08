__version__ = "0.1.0"

# Load the permanent curriculum extension before runtime modules import the
# learning ledger.  The enhanced class is a strict subclass, so every existing
# RishiLearningLedger API remains compatible while KRISHNA gains curriculum,
# evidence-gated assessment and daily queue capabilities without a second
# resident learning runtime.
from . import rishi_learning as _rishi_learning
from .rishi_curriculum import CurriculumRishiLearningLedger

_rishi_learning.RishiLearningLedger = CurriculumRishiLearningLedger

del _rishi_learning
