"""
Investigation Service for SUS — Spike Understanding System.

This service acts as the orchestration layer between the API and the ML
pipeline. It is responsible for:

1. Accepting investigation requests
2. Running the ML pipeline (feature engineering → spike detection → classification)
3. Converting raw pipeline output into clean domain models
4. Generating incident records
5. Returning structured investigation results

Design principles:
- This service DOES NOT contain ML logic. It delegates to existing modules.
- This service DOES NOT do HTTP/serialization. It returns domain models.
- pandas DataFrames stay inside this service boundary; the outside world
  only sees Pydantic models.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from src.cause_classifier import load_model
from src.domain.enums import (
    ConfidenceBand,
    IncidentSeverity,
    IncidentStatus,
    PipelineClassification,
)
from src.domain.models import Incident, PipelineSummary
from src.incidents import classify_severity, generate_recommended_action
from src.pipeline import (
    STATUS_BASELINE,
    STATUS_FRAUD_SPIKE,
    STATUS_ORGANIC_SPIKE,
    STATUS_REVIEW_REQUIRED,
    get_pipeline_summary,
    run_pipeline,
)
from src.repositories.investigation_repository import InvestigationRepository
from src.services._helpers import extract_signals, safe_float, safe_str
from src.spike_detector import DEFAULT_Z_THRESHOLD, MIN_HISTORY_DAYS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline Result Conversion
# ---------------------------------------------------------------------------


def _map_classification(final_status: str) -> PipelineClassification:
    """Map pipeline string status to domain enum."""
    mapping = {
        STATUS_BASELINE: PipelineClassification.BASELINE,
        STATUS_ORGANIC_SPIKE: PipelineClassification.ORGANIC_SPIKE,
        STATUS_FRAUD_SPIKE: PipelineClassification.FRAUD_SPIKE,
        STATUS_REVIEW_REQUIRED: PipelineClassification.REVIEW_REQUIRED,
    }
    return mapping.get(final_status, PipelineClassification.REVIEW_REQUIRED)


def _map_severity(severity_str: str) -> IncidentSeverity:
    """Map severity string to domain enum."""
    mapping = {
        "critical": IncidentSeverity.CRITICAL,
        "high": IncidentSeverity.HIGH,
        "medium": IncidentSeverity.MEDIUM,
        "low": IncidentSeverity.LOW,
    }
    return mapping.get(severity_str, IncidentSeverity.LOW)


def _map_confidence_band(band: Optional[str]) -> ConfidenceBand:
    """Map confidence band string to domain enum."""
    if band is None:
        return ConfidenceBand.LOW_CONFIDENCE
    mapping = {
        "high_confidence": ConfidenceBand.HIGH_CONFIDENCE,
        "ambiguous": ConfidenceBand.AMBIGUOUS,
        "low_confidence": ConfidenceBand.LOW_CONFIDENCE,
    }
    return mapping.get(band, ConfidenceBand.LOW_CONFIDENCE)


def _pipeline_row_to_incident(row: pd.Series) -> Optional[Incident]:
    """Convert a single pipeline result row to an Incident domain model.

    Returns None for baseline and organic_spike windows (no incident generated).
    """
    final_status = row.get("final_status", "")

    # Only create incidents for fraud_spike and review_required
    if final_status not in {STATUS_FRAUD_SPIKE, STATUS_REVIEW_REQUIRED}:
        return None

    fraud_prob = safe_float(row.get("fraud_probability"), 0.0)
    anomaly_score = safe_float(row.get("volume_zscore_7d"), 0.0)
    confidence_val = safe_float(row.get("confidence"), 0.0)
    confidence_band_str = safe_str(row.get("confidence_band"), "low_confidence")

    severity_str = classify_severity(
        fraud_prob, anomaly_score, confidence_band_str, final_status
    )
    predicted_cause = row.get("predicted_cause")
    if pd.isna(predicted_cause):
        predicted_cause = None
    recommended_action = generate_recommended_action(
        final_status, severity_str, confidence_band_str, predicted_cause
    )
    incident_id = f"INC-{row['merchant_id']}-{str(row['date'])[:10].replace('-', '')}"

    return Incident(
        id=incident_id,
        merchant_id=row["merchant_id"],
        date=str(row["date"])[:10],
        severity=_map_severity(severity_str),
        status=IncidentStatus.OPEN,
        classification=_map_classification(final_status),
        predicted_cause=str(predicted_cause) if predicted_cause else None,
        fraud_probability=fraud_prob,
        confidence=confidence_val,
        confidence_band=_map_confidence_band(confidence_band_str),
        anomaly_score=anomaly_score,
        decision_reason=safe_str(row.get("decision_reason"), ""),
        anomaly_summary=safe_str(row.get("anomaly_summary"), ""),
        top_signals=extract_signals(row),
        recommended_action=recommended_action,
    )


# ---------------------------------------------------------------------------
# Investigation Service
# ---------------------------------------------------------------------------


class InvestigationService:
    """Orchestrates investigations through the SUS ML pipeline.

    This is the primary service interface for the investigations API.
    It encapsulates all pipeline orchestration and domain model conversion.
    """

    # Sentinel value: signals that the caller explicitly wants to clear
    # the merchant_filter (as opposed to "not provided" which keeps original).
    _CLEAR_MERCHANT_FILTER = object()

    def run_investigation(
        self,
        transactions_path: str = "data/raw/transactions.csv",
        window_labels_path: str = "data/raw/window_labels.csv",
        model_path: Optional[str] = None,
        z_threshold: float = DEFAULT_Z_THRESHOLD,
        min_history_days: int = MIN_HISTORY_DAYS,
        merchant_filter: Optional[str] = None,
        db: Optional[Session] = None,
        dataset_id: Optional[str] = None,
        data_source_name: Optional[str] = None,
    ) -> dict:
        """Run a complete investigation through the SUS pipeline.

        Args:
            transactions_path: Path to the raw transactions CSV.
            window_labels_path: Path to the window labels CSV.
            model_path: Optional custom model path. Uses default if None.
            z_threshold: Z-score threshold for Stage 1 spike detection.
            min_history_days: Minimum historical days for spike detection.
            merchant_filter: If set, filter results to this merchant.
            db: Optional database session. When provided, results are persisted.
            dataset_id: Optional dataset ID from uploaded data.
            data_source_name: Label identifying the data source.

        Returns:
            Dictionary with:
              - investigation_id: Unique run identifier
              - summary: PipelineSummary model
              - incidents: List of IncidentResponse-compatible dicts
              - total_results: Total windows processed
              - processing_note: Any warnings from the run
        """
        investigation_id = f"INV-{uuid.uuid4().hex[:12].upper()}"
        processing_note = ""
        effective_source_name = data_source_name or "default"

        logger.info(
            "Starting investigation %s (threshold=%.2f, merchant=%s, source=%s)",
            investigation_id,
            z_threshold,
            merchant_filter or "all",
            effective_source_name,
        )

        # Load data
        logger.info("Loading transactions from %s", transactions_path)
        try:
            transactions = pd.read_csv(transactions_path)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Data file not found: {e.filename}. "
                "Ensure the pipeline data has been generated."
            ) from e

        # Load or generate window labels
        if window_labels_path:
            logger.info("Loading window labels from %s", window_labels_path)
            try:
                window_labels = pd.read_csv(window_labels_path)
            except FileNotFoundError:
                # Window labels file missing — generate from transactions
                logger.warning(
                    "Window labels file not found at %s — generating from transactions",
                    window_labels_path,
                )
                window_labels = self._generate_window_labels(transactions)
        else:
            # No window labels path provided (e.g. uploaded dataset without
            # a companion labels file).  Generate from the transactions.
            logger.info("No window labels provided — generating from transactions")
            window_labels = self._generate_window_labels(transactions)

        logger.info(
            "Loaded %d transactions, %d window labels",
            len(transactions), len(window_labels),
        )

        # Run the core pipeline
        logger.info("Running SUS pipeline...")
        pipeline_results = run_pipeline(
            transactions,
            window_labels,
            model_path=model_path,
            z_threshold=z_threshold,
            min_history_days=min_history_days,
        )

        # Filter to specific merchant if requested
        if merchant_filter:
            pipeline_results = pipeline_results[
                pipeline_results["merchant_id"] == merchant_filter
            ].copy()
            if len(pipeline_results) == 0:
                processing_note = f"No results found for merchant '{merchant_filter}'"

        # Generate pipeline summary
        raw_summary = get_pipeline_summary(pipeline_results)
        summary = PipelineSummary(
            total_windows=raw_summary["total_windows"],
            spikes_detected=raw_summary["n_spikes_detected"],
            spike_rate=raw_summary["spike_rate"],
            fraud_incidents=raw_summary["n_fraud_spike"],
            organic_incidents=raw_summary["n_organic_spike"],
            review_required=raw_summary["n_review_required"],
            baseline_windows=raw_summary["n_baseline"],
        )

        # Convert pipeline results to domain Incident models
        logger.info("Converting pipeline results to domain models...")
        incidents = []
        for _, row in pipeline_results.iterrows():
            incident = _pipeline_row_to_incident(row)
            if incident is not None:
                incidents.append(incident)

        logger.info(
            "Investigation %s complete: %d incidents from %d windows",
            investigation_id,
            len(incidents),
            len(pipeline_results),
        )

        result = {
            "investigation_id": investigation_id,
            "summary": summary,
            "incidents": incidents,
            "total_results": len(pipeline_results),
            "processing_note": processing_note,
            # Capture input parameters for persistence
            "_input": {
                "transactions_path": transactions_path,
                "window_labels_path": window_labels_path,
                "model_path": model_path,
                "z_threshold": z_threshold,
                "min_history_days": min_history_days,
                "merchant_filter": merchant_filter,
                "dataset_id": dataset_id,
                "data_source_name": effective_source_name,
            },
        }

        # Persist if database session provided
        if db is not None:
            self._persist_results(db, result)

        return result

    @staticmethod
    def _generate_window_labels(transactions: pd.DataFrame) -> pd.DataFrame:
        """Generate window labels from transaction data.

        Creates one window per merchant per date with a synthetic label.
        This is used when no explicit window labels file is provided
        (e.g. uploaded CSV datasets without a companion labels file).
        """
        counts = (
            transactions.groupby(["merchant_id", "date"])
            .size()
            .reset_index(name="transaction_count")
        )
        counts["window_label"] = "unknown"
        return counts

    def _persist_results(self, db: Session, result: dict) -> None:
        """Persist investigation results to the database.

        Creates an InvestigationRun and all associated PersistedIncident records.
        On failure, rolls back and logs a warning — the API response is
        still returned to the caller (degraded mode).
        """
        repo = InvestigationRepository(db)
        input_params = result["_input"]
        summary = result["summary"]

        try:
            run = repo.create_investigation(
                investigation_id=result["investigation_id"],
                dataset_id=input_params.get("dataset_id"),
                transactions_path=input_params["transactions_path"],
                window_labels_path=input_params["window_labels_path"],
                model_path=input_params["model_path"],
                z_threshold=input_params["z_threshold"],
                min_history_days=input_params["min_history_days"],
                merchant_filter=input_params["merchant_filter"],
                total_results=result["total_results"],
                spikes_detected=summary.spikes_detected,
                fraud_incidents=summary.fraud_incidents,
                organic_incidents=summary.organic_incidents,
                review_required=summary.review_required,
                baseline_windows=summary.baseline_windows,
                spike_rate=summary.spike_rate,
                processing_note=result["processing_note"],
            )

            for incident in result["incidents"]:
                repo.create_incident(
                    investigation_run_id=run.id,
                    incident_id=incident.id,
                    merchant_id=incident.merchant_id,
                    date=incident.date,
                    severity=incident.severity.value,
                    status=incident.status.value,
                    classification=incident.classification.value,
                    predicted_cause=incident.predicted_cause,
                    fraud_probability=incident.fraud_probability,
                    confidence=incident.confidence,
                    confidence_band=incident.confidence_band.value,
                    anomaly_score=incident.anomaly_score,
                    decision_reason=incident.decision_reason,
                    anomaly_summary=incident.anomaly_summary,
                    top_signals_json=json.dumps(incident.top_signals),
                    recommended_action=incident.recommended_action,
                )

            db.commit()
            logger.info(
                "Persisted investigation %s (%d incidents)",
                result["investigation_id"],
                len(result["incidents"]),
            )
        except Exception:
            db.rollback()
            logger.warning(
                "Failed to persist investigation %s — returning results without persistence",
                result["investigation_id"],
                exc_info=True,
            )

    def _load_original_config(
        self,
        investigation_id: str,
        db: Session,
    ) -> "InvestigationRun":
        """Load and validate the original investigation for rerun.

        Shared by rerun_investigation() and rerun_investigation_with_config().
        Returns the ORM object. Raises ValueError if not found.
        """
        repo = InvestigationRepository(db)
        original = repo.get_by_investigation_id(investigation_id)
        if original is None:
            raise ValueError(f"Investigation '{investigation_id}' not found")
        return original

    def rerun_investigation(
        self,
        investigation_id: str,
        db: Session,
    ) -> dict:
        """Re-run a previously completed investigation using its stored configuration.

        Looks up the original investigation, extracts input parameters,
        and delegates to run_investigation(). Creates a brand new
        investigation — the original is never modified.

        Args:
            investigation_id: The business ID of the investigation to re-run.
            db: Active database session.

        Returns:
            Dictionary with the new investigation results (same shape as
            run_investigation output).

        Raises:
            ValueError: If the original investigation is not found.
        """
        original = self._load_original_config(investigation_id, db)

        logger.info(
            "Re-running investigation %s with original configuration",
            investigation_id,
        )

        # Extract stored configuration and run a fresh investigation
        return self.run_investigation(
            transactions_path=original.transactions_path,
            window_labels_path=original.window_labels_path,
            model_path=original.model_path,
            z_threshold=original.z_threshold,
            min_history_days=original.min_history_days,
            merchant_filter=original.merchant_filter,
            db=db,
        )

    def rerun_investigation_with_config(
        self,
        investigation_id: str,
        db: Session,
        z_threshold: float | None = None,
        min_history_days: int | None = None,
        merchant_filter: str | None | object = None,
    ) -> dict:
        """Re-run an investigation with optional parameter overrides.

        Loads the original configuration, applies any non-None overrides,
        and delegates to run_investigation(). The original investigation
        is never modified.

        Args:
            investigation_id: The business ID of the investigation to re-run.
            db: Active database session.
            z_threshold: Override for z-score threshold (None = keep original).
            min_history_days: Override for min history days (None = keep original).
            merchant_filter: Override for merchant filter. None = keep original.
                Pass the sentinel _CLEAR_MERCHANT_FILTER to explicitly clear it.

        Returns:
            Dictionary with the new investigation results.

        Raises:
            ValueError: If the original investigation is not found.
        """
        original = self._load_original_config(investigation_id, db)

        # Merge overrides: use override value if provided, else original
        effective_z = z_threshold if z_threshold is not None else original.z_threshold
        effective_min = min_history_days if min_history_days is not None else original.min_history_days

        if merchant_filter is InvestigationService._CLEAR_MERCHANT_FILTER:
            effective_merchant = None  # Explicitly clear the filter
        elif merchant_filter is not None:
            # User provided a value — normalize it
            effective_merchant = merchant_filter.strip() or None
        else:
            effective_merchant = original.merchant_filter

        logger.info(
            "Re-running investigation %s with overrides: z=%.2f, min_days=%d, merchant=%s",
            investigation_id,
            effective_z,
            effective_min,
            effective_merchant or "all",
        )

        return self.run_investigation(
            transactions_path=original.transactions_path,
            window_labels_path=original.window_labels_path,
            model_path=original.model_path,
            z_threshold=effective_z,
            min_history_days=effective_min,
            merchant_filter=effective_merchant,
            db=db,
        )

    def get_investigation_status(self) -> dict:
        """Return a lightweight status check for the pipeline.

        Useful for the API to verify the pipeline is operational.
        """
        from src.config import settings

        model_loaded = False
        try:
            load_model()
            model_loaded = True
        except (FileNotFoundError, Exception):
            pass

        return {
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "pipeline_ready": model_loaded,
        }


# Module-level singleton for dependency injection
investigation_service = InvestigationService()
