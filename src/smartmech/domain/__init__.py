"""Domain layer: pure entities, value objects, schemas, invariants."""

from smartmech.domain.artifact import (
    ProvenanceManifest,
    compute_artifact_key,
    compute_canonical_input_hash,
)
from smartmech.domain.autonomy import AutonomyLevel, PrivacyStatus, PublishMetadata
from smartmech.domain.budget import BudgetConfig, BudgetExceededError, CostRecord
from smartmech.domain.capabilities import AdapterCapabilities
from smartmech.domain.concept import (
    Concept,
    Keyframe,
    Plan,
    Script,
    ShotList,
    SiteBible,
    Transition,
)
from smartmech.domain.qc import (
    GateEvaluation,
    QCGateStatus,
    QCMetrics,
    QCReport,
    VLMCritique,
)
from smartmech.domain.strategy import ChainStrategy, TailTrimPolicy

__all__ = [
    "AdapterCapabilities",
    "AutonomyLevel",
    "BudgetConfig",
    "BudgetExceededError",
    "ChainStrategy",
    "Concept",
    "CostRecord",
    "GateEvaluation",
    "Keyframe",
    "Plan",
    "PrivacyStatus",
    "ProvenanceManifest",
    "PublishMetadata",
    "QCGateStatus",
    "QCMetrics",
    "QCReport",
    "Script",
    "ShotList",
    "SiteBible",
    "TailTrimPolicy",
    "Transition",
    "VLMCritique",
    "compute_artifact_key",
    "compute_canonical_input_hash",
]
