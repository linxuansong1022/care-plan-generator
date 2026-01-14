"""
Order services.

Re-exports duplicate detection classes from duplicate_detection.py for backwards compatibility.
"""

from .duplicate_detection import (
    DuplicateCheckResult,
    DuplicateDetectionService,
    FullDuplicateCheckResult,
    OrderDuplicateDetector,
    PatientDuplicateDetector,
    ProviderDuplicateDetector,
    Warning,
)

__all__ = [
    "Warning",
    "DuplicateCheckResult",
    "ProviderDuplicateDetector",
    "PatientDuplicateDetector",
    "OrderDuplicateDetector",
    "FullDuplicateCheckResult",
    "DuplicateDetectionService",
]
