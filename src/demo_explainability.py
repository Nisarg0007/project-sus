"""
Demonstration of SUS Explainability and Incident Layers

Runs the complete system and shows representative incidents.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

from src.pipeline import run_pipeline
from src.cause_classifier import load_model, get_default_feature_set
from src.explainability import explain_windows_batch
from src.incidents import generate_incidents_batch, get_incident_summary


def main():
    """Run the complete demonstration."""
    print("=" * 70)
    print("SUS - EXPLAINABILITY & INCIDENT INTELLIGENCE DEMO")
    print("=" * 70)

    # Load data
    print("\n[1/5] Loading data...")
    transactions = pd.read_csv("data/raw/transactions.csv")
    window_labels = pd.read_csv("data/raw/window_labels.csv")
    print(f"  Transactions: {len(transactions):,}")
    print(f"  Window labels: {len(window_labels)}")

    # Run pipeline
    print("\n[2/5] Running pipeline...")
    pipeline_results = run_pipeline(transactions, window_labels)

    # Load model for explainability
    print("\n[3/5] Generating explanations...")
    model_artifact = load_model()
    model = model_artifact["model"]
    feature_cols = model_artifact["feature_cols"]

    # Load window features for historical comparison
    window_features = pd.read_csv("data/processed/window_features.csv")
    window_features["date"] = pd.to_datetime(window_features["date"])

    # Merge behavioral features into pipeline results for explainability
    pipeline_with_features = pipeline_results.merge(
        window_features[feature_cols + ["merchant_id", "date"]],
        on=["merchant_id", "date"],
        how="left",
        suffixes=("", "_from_features")
    )

    # Generate explanations for all detected spikes
    explained_results = explain_windows_batch(
        pipeline_with_features, window_features, model, feature_cols
    )

    # Generate incidents
    print("\n[4/5] Generating incidents...")
    incidents_df = generate_incidents_batch(
        explained_results,
        anomaly_summaries=explained_results["anomaly_summary"],
        top_fraud_signals=explained_results["top_fraud_signal"],
        explanation_texts=explained_results["explanation_text"],
    )

    # Save incidents
    incidents_path = "data/processed/incidents.csv"
    os.makedirs("data/processed", exist_ok=True)
    incidents_df.to_csv(incidents_path, index=False)
    print(f"  Saved {len(incidents_df)} incidents to: {incidents_path}")

    # Print summary
    print("\n[5/5] Summary...")
    summary = get_incident_summary(incidents_df)

    print(f"\n{'='*60}")
    print("INCIDENT SUMMARY")
    print(f"{'='*60}")
    print(f"  Total incidents: {summary['total_incidents']}")
    print(f"\n  Severity distribution:")
    for severity, count in summary.get("severity_distribution", {}).items():
        print(f"    {severity}: {count}")
    print(f"\n  Status distribution:")
    for status, count in summary.get("status_distribution", {}).items():
        print(f"    {status}: {count}")

    # Show representative incidents
    print(f"\n{'='*60}")
    print("REPRESENTATIVE INCIDENTS")
    print(f"{'='*60}")

    # Find representative incidents
    fraud_incidents = incidents_df[incidents_df["final_status"] == "fraud_spike"]
    review_incidents = incidents_df[incidents_df["final_status"] == "review_required"]

    # High confidence fraud
    if len(fraud_incidents) > 0:
        high_conf_fraud = fraud_incidents[fraud_incidents["confidence_band"] == "high_confidence"]
        if len(high_conf_fraud) > 0:
            incident = high_conf_fraud.iloc[0]
            print(f"\n--- HIGH-CONFIDENCE FRAUD INCIDENT ---")
            _print_incident(incident)

    # Other fraud incident
    if len(fraud_incidents) > 1:
        other_fraud = fraud_incidents[fraud_incidents["confidence_band"] != "high_confidence"]
        if len(other_fraud) > 0:
            incident = other_fraud.iloc[0]
            print(f"\n--- OTHER FRAUD INCIDENT ---")
            _print_incident(incident)

    # Review required
    if len(review_incidents) > 0:
        incident = review_incidents.iloc[0]
        print(f"\n--- REVIEW REQUIRED INCIDENT ---")
        _print_incident(incident)

    # Show sample explained results
    print(f"\n{'='*60}")
    print("SAMPLE EXPLAINED RESULTS (first 5 detected spikes)")
    print(f"{'='*60}")

    spike_results = explained_results[explained_results["is_spike"] == True].head(5)
    display_cols = ["merchant_id", "date", "final_status", "confidence",
                    "anomaly_summary", "top_fraud_signal"]
    print(spike_results[display_cols].to_string(index=False))

    print(f"\n{'='*60}")
    print("Demo complete!")
    print(f"{'='*60}")


def _print_incident(incident):
    """Print a single incident record."""
    print(f"  Incident ID: {incident['incident_id']}")
    print(f"  Merchant: {incident['merchant_id']}")
    print(f"  Date: {incident['date']}")
    print(f"  Severity: {incident['severity']}")
    print(f"  Status: {incident['final_status']}")
    print(f"  Fraud Probability: {incident['fraud_probability']:.3f}")
    print(f"  Confidence Band: {incident['confidence_band']}")
    print(f"  Anomaly Summary: {incident['anomaly_summary'][:100]}...")
    print(f"  Recommended Action: {incident['recommended_action'][:100]}...")


if __name__ == "__main__":
    main()
