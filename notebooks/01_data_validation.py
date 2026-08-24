"""
SUS Data Validation Script
==========================

Validates whether the synthetic dataset supports the central hypothesis:
Transaction volume alone should NOT reliably distinguish organic from fraud spikes.

Usage:
    python notebooks/01_data_validation.py

Outputs:
    - Printed analysis to terminal
    - Charts saved to docs/validation_outputs/
"""

from __future__ import annotations

import os
import sys

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

TRANSACTIONS_PATH = "data/raw/transactions.csv"
WINDOW_LABELS_PATH = "data/raw/window_labels.csv"
OUTPUT_DIR = "docs/validation_outputs"


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the generated dataset."""
    txn = pd.read_csv(TRANSACTIONS_PATH, parse_dates=["timestamp", "date"])
    labels = pd.read_csv(WINDOW_LABELS_PATH, parse_dates=["date"])
    return txn, labels


# ---------------------------------------------------------------------------
# Analysis 1: Window-level volume distributions
# ---------------------------------------------------------------------------

def analysis_1_volume_distributions(labels: pd.DataFrame) -> None:
    """Report volume statistics by class and overlap diagnostics."""
    print("\n" + "=" * 70)
    print("ANALYSIS 1: Window-Level Volume Distributions")
    print("=" * 70)

    classes = ["baseline", "organic_spike", "fraud_spike"]

    for cls in classes:
        subset = labels[labels["window_label"] == cls]["transaction_count"]
        print(f"\n  {cls.upper()}")
        print(f"    count:    {subset.count():>8d}")
        print(f"    mean:     {subset.mean():>10.1f}")
        print(f"    median:   {subset.median():>10.1f}")
        print(f"    std:      {subset.std():>10.1f}")
        print(f"    min:      {subset.min():>10.0f}")
        print(f"    max:      {subset.max():>10.0f}")
        print(f"    25th pct: {subset.quantile(0.25):>10.1f}")
        print(f"    75th pct: {subset.quantile(0.75):>10.1f}")

    # Overlap diagnostics
    organic = labels[labels["window_label"] == "organic_spike"]["transaction_count"]
    fraud = labels[labels["window_label"] == "fraud_spike"]["transaction_count"]

    fraud_min, fraud_max = fraud.min(), fraud.max()
    organic_min, organic_max = organic.min(), organic.max()

    organic_in_fraud = ((organic >= fraud_min) & (organic <= fraud_max)).mean() * 100
    fraud_in_organic = ((fraud >= organic_min) & (fraud <= organic_max)).mean() * 100

    print("\n  OVERLAP DIAGNOSTICS (organic_spike vs fraud_spike)")
    print(f"    Organic windows within fraud range: {organic_in_fraud:.1f}%")
    print(f"    Fraud windows within organic range: {fraud_in_organic:.1f}%")
    print(f"    Fraud volume range:    [{fraud_min:.0f}, {fraud_max:.0f}]")
    print(f"    Organic volume range:  [{organic_min:.0f}, {organic_max:.0f}]")


# ---------------------------------------------------------------------------
# Analysis 2: Volume-only classification baseline
# ---------------------------------------------------------------------------

def analysis_2_volume_only_classifier(labels: pd.DataFrame) -> None:
    """Train a volume-only classifier on organic vs fraud."""
    print("\n" + "=" * 70)
    print("ANALYSIS 2: Volume-Only Classification Baseline")
    print("=" * 70)

    # Filter to organic and fraud only
    spike_labels = labels[labels["window_label"].isin(["organic_spike", "fraud_spike"])].copy()
    spike_labels["target"] = (spike_labels["window_label"] == "fraud_spike").astype(int)

    X = spike_labels[["transaction_count"]].values
    y = spike_labels["target"].values

    print(f"\n  Dataset: {len(spike_labels)} spike windows")
    print(f"  Organic: {(y == 0).sum()}, Fraud: {(y == 1).sum()}")

    # Stratified split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    # Train logistic regression (no tuning)
    model = LogisticRegression(random_state=42, max_iter=1000)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)

    print(f"\n  Logistic Regression on transaction_count only:")
    print(f"    Accuracy:  {acc:.4f}")
    print(f"    Precision: {prec:.4f}")
    print(f"    Recall:    {rec:.4f}")
    print(f"    F1 Score:  {f1:.4f}")
    print(f"\n  Confusion matrix (rows=actual, cols=predicted):")
    print(f"    {'':>20s} Pred Organic  Pred Fraud")
    print(f"    {'Actual Organic':>20s}  {cm[0][0]:>6d}      {cm[0][1]:>6d}")
    print(f"    {'Actual Fraud':>20s}  {cm[1][0]:>6d}      {cm[1][1]:>6d}")

    # Interpretation
    print(f"\n  INTERPRETATION:")
    if acc < 0.75:
        print(f"    Volume-only accuracy is {acc:.1%} — below 75%.")
        print(f"    Transaction volume ALONE is insufficient to distinguish spike causes.")
        print(f"    This validates the SUS hypothesis.")
    elif acc < 0.85:
        print(f"    Volume-only accuracy is {acc:.1%} — moderate.")
        print(f"    Volume provides some signal but is not decisive.")
        print(f"    Behavioral features are needed for reliable classification.")
    else:
        print(f"    Volume-only accuracy is {acc:.1%} — suspiciously high.")
        print(f"    Volume may be overly separable. Check for leakage.")


# ---------------------------------------------------------------------------
# Analysis 3: Label distribution per merchant
# ---------------------------------------------------------------------------

def analysis_3_per_merchant_distribution(labels: pd.DataFrame) -> None:
    """Show label distribution and volume per merchant."""
    print("\n" + "=" * 70)
    print("ANALYSIS 3: Label Distribution Per Merchant")
    print("=" * 70)

    print(f"\n  {'Merchant':<15s} {'Baseline':>8s} {'Organic':>8s} {'Fraud':>8s} {'Avg Vol':>10s}")
    print(f"  {'-'*15} {'-'*8} {'-'*8} {'-'*8} {'-'*10}")

    for merchant_id in sorted(labels["merchant_id"].unique()):
        m = labels[labels["merchant_id"] == merchant_id]
        b = (m["window_label"] == "baseline").sum()
        o = (m["window_label"] == "organic_spike").sum()
        f = (m["window_label"] == "fraud_spike").sum()
        avg_vol = m["transaction_count"].mean()
        print(f"  {merchant_id:<15s} {b:>8d} {o:>8d} {f:>8d} {avg_vol:>10.0f}")

    # Check for identical patterns
    print(f"\n  CHECK: Are spike distributions identical across merchants?")
    spike_counts = labels.groupby("merchant_id")["window_label"].value_counts().unstack(fill_value=0)
    if spike_counts.drop(columns="baseline").duplicated().any():
        print("    WARNING: Some merchants have identical spike distributions.")
    else:
        print("    OK: Each merchant has a distinct spike distribution.")


# ---------------------------------------------------------------------------
# Analysis 4: Basic behavioral sanity checks
# ---------------------------------------------------------------------------

def analysis_4_behavioral_sanity(txn: pd.DataFrame, labels: pd.DataFrame) -> None:
    """Compute preliminary window-level behavioral stats by class."""
    print("\n" + "=" * 70)
    print("ANALYSIS 4: Behavioral Sanity Checks")
    print("=" * 70)

    # Compute window-level features
    window_features = txn.groupby(["merchant_id", "date"]).agg(
        txn_count=("transaction_id", "count"),
        unique_skus=("sku_id", "nunique"),
        unique_devices=("device_id", "nunique"),
        unique_ips=("ip_id", "nunique"),
        failed_rate=("payment_status", lambda x: (x == "failed").mean()),
        retry_rate=("is_retry", "mean"),
        new_customer_share=("customer_is_new", "mean"),
        unique_customers=("customer_id", "nunique"),
    ).reset_index()

    window_features["sku_ratio"] = window_features["unique_skus"] / window_features["txn_count"]
    window_features["repeat_customer_share"] = 1.0 - window_features["new_customer_share"]

    # Merge with labels
    merged = labels.merge(window_features, on=["merchant_id", "date"])

    features_to_check = [
        "sku_ratio",
        "failed_rate",
        "retry_rate",
        "unique_devices",
        "unique_ips",
        "new_customer_share",
        "repeat_customer_share",
    ]

    print(f"\n  {'Feature':<25s} {'Class':<16s} {'Mean':>8s} {'Median':>8s}")
    print(f"  {'-'*25} {'-'*16} {'-'*8} {'-'*8}")

    for feat in features_to_check:
        for cls in ["organic_spike", "fraud_spike"]:
            subset = merged[merged["window_label"] == cls][feat]
            print(f"  {feat:<25s} {cls:<16s} {subset.mean():>8.4f} {subset.median():>8.4f}")
        print()

    # Check overlap
    print("  OVERLAP CHECK: Do organic and fraud have distinguishable tendencies?")
    for feat in features_to_check:
        org_vals = merged[merged["window_label"] == "organic_spike"][feat]
        fraud_vals = merged[merged["window_label"] == "fraud_spike"][feat]

        org_min, org_max = org_vals.min(), org_vals.max()
        fraud_min, fraud_max = fraud_vals.min(), fraud_vals.max()

        overlap = max(0, min(org_max, fraud_max) - max(org_min, fraud_min))
        range_size = max(org_max, fraud_max) - min(org_min, fraud_min)
        overlap_pct = (overlap / range_size * 100) if range_size > 0 else 0

        print(f"    {feat:<25s} overlap range: {overlap_pct:.1f}%")


# ---------------------------------------------------------------------------
# Analysis 5: Check for suspiciously easy separation
# ---------------------------------------------------------------------------

def analysis_5_suspicious_separation(txn: pd.DataFrame, labels: pd.DataFrame) -> None:
    """Look for synthetic data artifacts or perfect separation."""
    print("\n" + "=" * 70)
    print("ANALYSIS 5: Suspiciously Easy Separation Check")
    print("=" * 70)

    # Compute window-level features
    window_features = txn.groupby(["merchant_id", "date"]).agg(
        txn_count=("transaction_id", "count"),
        unique_skus=("sku_id", "nunique"),
        unique_devices=("device_id", "nunique"),
        unique_ips=("ip_id", "nunique"),
        failed_rate=("payment_status", lambda x: (x == "failed").mean()),
        retry_rate=("is_retry", "mean"),
        new_customer_share=("customer_is_new", "mean"),
        unique_customers=("customer_id", "nunique"),
    ).reset_index()

    window_features["sku_ratio"] = window_features["unique_skus"] / window_features["txn_count"]

    merged = labels.merge(window_features, on=["merchant_id", "date"])

    # Filter to spike windows only
    spikes = merged[merged["window_label"].isin(["organic_spike", "fraud_spike"])].copy()
    spikes["is_fraud"] = (spikes["window_label"] == "fraud_spike").astype(int)

    checks = [
        ("txn_count", "Transaction volume"),
        ("sku_ratio", "SKU diversity ratio"),
        ("failed_rate", "Failed payment rate"),
        ("retry_rate", "Retry rate"),
        ("unique_devices", "Unique device count"),
        ("new_customer_share", "New customer share"),
    ]

    print()
    any_suspicious = False

    for col, name in checks:
        org = spikes[spikes["is_fraud"] == 0][col]
        fraud = spikes[spikes["is_fraud"] == 1][col]

        org_max = org.max()
        fraud_min = fraud.min()

        # Check 1: Complete non-overlap (one class entirely above the other)
        no_overlap = org_max < fraud_min or fraud.max() < org.min()

        # Check 2: Perfect threshold separation
        # Find best single-threshold accuracy
        thresholds = np.linspace(
            min(org.min(), fraud.min()),
            max(org.max(), fraud.max()),
            200,
        )
        best_acc = 0
        for t in thresholds:
            # Try both directions
            pred_fraud_dir1 = (spikes[col] >= t).astype(int)
            pred_fraud_dir2 = (spikes[col] <= t).astype(int)
            acc1 = (pred_fraud_dir1 == spikes["is_fraud"]).mean()
            acc2 = (pred_fraud_dir2 == spikes["is_fraud"]).mean()
            best_acc = max(best_acc, acc1, acc2)

        status = "OK"
        if no_overlap:
            status = "SUSPICIOUS: Complete non-overlap"
            any_suspicious = True
        elif best_acc >= 0.99:
            status = f"SUSPICIOUS: Single threshold achieves {best_acc:.1%} accuracy"
            any_suspicious = True
        elif best_acc >= 0.95:
            status = f"WARNING: Single threshold achieves {best_acc:.1%} accuracy"

        print(f"  {name:<25s} best threshold acc: {best_acc:.1%}  [{status}]")

    print()
    if any_suspicious:
        print("  RESULT: SUSPICIOUS SEPARATION DETECTED")
        print("  The dataset may have artifacts that make classification trivially easy.")
        print("  Generator may need adjustment.")
    else:
        print("  RESULT: No suspiciously easy separation found.")
        print("  Organic and fraud spikes have overlapping distributions.")
        print("  The classification task appears non-trivial.")


# ---------------------------------------------------------------------------
# Chart generation
# ---------------------------------------------------------------------------

def generate_charts(labels: pd.DataFrame, txn: pd.DataFrame) -> None:
    """Generate validation charts."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- Chart 1: Volume distribution ---
    fig, ax = plt.subplots(figsize=(10, 6))

    classes = ["baseline", "organic_spike", "fraud_spike"]
    colors = ["#2ecc71", "#3498db", "#e74c3c"]

    for cls, color in zip(classes, colors):
        subset = labels[labels["window_label"] == cls]["transaction_count"]
        ax.hist(subset, bins=30, alpha=0.6, color=color, label=cls, edgecolor="white")

    ax.set_xlabel("Transaction Count", fontsize=12)
    ax.set_ylabel("Frequency", fontsize=12)
    ax.set_title("Window-Level Transaction Volume by Class", fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "volume_distribution.png"), dpi=150)
    plt.close()
    print(f"\n  Saved: {OUTPUT_DIR}/volume_distribution.png")

    # --- Chart 2: Behavioral feature comparison ---
    # Compute window-level features
    window_features = txn.groupby(["merchant_id", "date"]).agg(
        txn_count=("transaction_id", "count"),
        unique_skus=("sku_id", "nunique"),
        failed_rate=("payment_status", lambda x: (x == "failed").mean()),
        retry_rate=("is_retry", "mean"),
        new_customer_share=("customer_is_new", "mean"),
    ).reset_index()

    window_features["sku_ratio"] = window_features["unique_skus"] / window_features["txn_count"]
    merged = labels.merge(window_features, on=["merchant_id", "date"])

    features = [
        ("txn_count", "Transaction Count"),
        ("sku_ratio", "SKU Diversity Ratio"),
        ("failed_rate", "Failed Payment Rate"),
        ("retry_rate", "Retry Rate"),
        ("new_customer_share", "New Customer Share"),
    ]

    fig, axes = plt.subplots(1, 5, figsize=(22, 5))

    for ax, (col, title) in zip(axes, features):
        spike_data = merged[merged["window_label"].isin(["organic_spike", "fraud_spike"])]

        for cls, color in zip(["organic_spike", "fraud_spike"], ["#3498db", "#e74c3c"]):
            subset = spike_data[spike_data["window_label"] == cls][col]
            ax.hist(subset, bins=20, alpha=0.6, color=color, label=cls, edgecolor="white")

        ax.set_title(title, fontsize=11)
        ax.set_ylabel("Frequency")
        ax.legend(fontsize=9)
        ax.grid(axis="y", alpha=0.3)

    plt.suptitle("Behavioral Features: Organic vs Fraud Spikes", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "behavioral_feature_comparison.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {OUTPUT_DIR}/behavioral_feature_comparison.png")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Run all validation analyses."""
    print("=" * 70)
    print("SUS Data Validation")
    print("=" * 70)

    txn, labels = load_data()
    print(f"\n  Loaded {len(txn):,} transactions")
    print(f"  Loaded {len(labels)} window labels")

    analysis_1_volume_distributions(labels)
    analysis_2_volume_only_classifier(labels)
    analysis_3_per_merchant_distribution(labels)
    analysis_4_behavioral_sanity(txn, labels)
    analysis_5_suspicious_separation(txn, labels)

    print("\n" + "=" * 70)
    print("Generating charts...")
    print("=" * 70)
    generate_charts(labels, txn)

    print("\n" + "=" * 70)
    print("Validation complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
