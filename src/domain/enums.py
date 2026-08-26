"""
Domain enums for SUS — Spike Understanding System.

These enums define the vocabulary of the system. They map directly to the
pipeline output statuses and incident lifecycle states.
"""

from enum import Enum


class IncidentSeverity(str, Enum):
    """Severity classification for incidents.

    Determined by the pipeline based on fraud probability, anomaly score,
    and confidence band. Maps directly to src/incidents.py classify_severity().
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IncidentStatus(str, Enum):
    """Operational status of an incident in the investigation workflow.

    Tracks the lifecycle from detection through resolution.
    """
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class PipelineClassification(str, Enum):
    """Final classification output from the SUS pipeline.

    These map directly to the final_status values produced by
    src/pipeline.py _assign_final_status().
    """
    BASELINE = "baseline"
    ORGANIC_SPIKE = "organic_spike"
    FRAUD_SPIKE = "fraud_spike"
    REVIEW_REQUIRED = "review_required"


class ConfidenceBand(str, Enum):
    """Model confidence band for cause classification.

    Determined by src/cause_classifier.py based on the predicted probability.
    HIGH: >= 0.80, AMBIGUOUS: 0.60-0.80, LOW: < 0.60
    """
    HIGH_CONFIDENCE = "high_confidence"
    AMBIGUOUS = "ambiguous"
    LOW_CONFIDENCE = "low_confidence"


class InvestigationStatus(str, Enum):
    """Status of an investigation session.

    An investigation groups one or more incidents under a single
    analyst inquiry.
    """
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"
