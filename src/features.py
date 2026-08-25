"""
Window-Level Feature Engineering for SUS 🤨

Aggregates transaction-level data into one feature row per merchant-day
(merchant_id + date = one window).

Usage:
    python -m src.features

Input:
    data/raw/transactions.csv

Output:
    data/processed/window_features.csv
"""

from __future__ import annotations

import os
import warnings
from typing import Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_TXN_COLUMNS = [
    "transaction_id",
    "merchant_id",
    "timestamp",
    "date",
    "window_label",
    "customer_id",
    "customer_is_new",
    "sku_id",
    "amount",
    "payment_status",
    "is_retry",
    "device_id",
    "ip_id",
]

# Metadata columns (not model features)
METADATA_COLUMNS = ["merchant_id", "date", "window_label"]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def safe_division(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divide safely, returning default if denominator is zero or NaN."""
    if denominator == 0 or np.isnan(denominator):
        return default
    result = numerator / denominator
    return default if np.isnan(result) else result


def shannon_entropy(counts: np.ndarray) -> float:
    """Calculate Shannon entropy from an array of counts.

    Higher entropy means more diversity (uniform distribution).
    Lower entropy means more concentration (skewed distribution).
    """
    total = counts.sum()
    if total == 0:
        return 0.0
    probs = counts / total
    # Remove zeros to avoid log(0)
    probs = probs[probs > 0]
    return float(-np.sum(probs * np.log2(probs)))


def compute_concentration_metrics(
    values: pd.Series,
) -> tuple[int, float, float, float]:
    """Compute diversity metrics for a categorical series.

    Returns:
        unique_count: Number of unique values
        diversity_ratio: unique_count / total_count
        top_share: Proportion of the most frequent value
        entropy: Shannon entropy
    """
    total = len(values)
    if total == 0:
        return 0, 0.0, 0.0, 0.0

    value_counts = values.value_counts()
    unique_count = len(value_counts)
    diversity_ratio = safe_division(unique_count, total)
    top_share = safe_division(value_counts.iloc[0], total) if len(value_counts) > 0 else 0.0
    entropy = shannon_entropy(value_counts.values)

    return unique_count, diversity_ratio, top_share, entropy


# ---------------------------------------------------------------------------
# Feature computation
# ---------------------------------------------------------------------------


def compute_window_features(window_txns: pd.DataFrame) -> dict:
    """Compute all behavioral features for a single merchant-day window.

    Args:
        window_txns: Transaction-level DataFrame for one merchant-day.

    Returns:
        Dictionary of feature name -> value.
    """
    n = len(window_txns)
    if n == 0:
        return {}

    features: dict = {}

    # --- 1. Volume and transaction features ---
    features["transaction_count"] = n
    features["successful_transaction_count"] = int(
        (window_txns["payment_status"] == "success").sum()
    )
    features["failed_transaction_count"] = int(
        (window_txns["payment_status"] == "failed").sum()
    )
    features["success_rate"] = safe_division(
        features["successful_transaction_count"], n
    )
    features["failed_payment_rate"] = safe_division(
        features["failed_transaction_count"], n
    )

    # --- 2. Transaction amount features ---
    amounts = window_txns["amount"].values
    features["amount_mean"] = float(np.mean(amounts))
    features["amount_median"] = float(np.median(amounts))
    features["amount_std"] = float(np.std(amounts, ddof=1)) if n > 1 else 0.0
    features["amount_min"] = float(np.min(amounts))
    features["amount_max"] = float(np.max(amounts))
    features["amount_p25"] = float(np.percentile(amounts, 25))
    features["amount_p75"] = float(np.percentile(amounts, 75))
    features["amount_iqr"] = features["amount_p75"] - features["amount_p25"]
    features["amount_cv"] = safe_division(features["amount_std"], features["amount_mean"])

    # --- 3. SKU diversity and concentration ---
    sku_unique, sku_diversity, sku_top_share, sku_entropy = compute_concentration_metrics(
        window_txns["sku_id"]
    )
    features["unique_sku_count"] = sku_unique
    features["sku_diversity_ratio"] = sku_diversity
    features["top_sku_share"] = sku_top_share
    features["sku_entropy"] = sku_entropy

    # --- 4. Retry and payment behavior ---
    features["retry_count"] = int(window_txns["is_retry"].sum())
    features["retry_rate"] = safe_division(features["retry_count"], n)
    features["failed_retry_count"] = int(
        ((window_txns["is_retry"]) & (window_txns["payment_status"] == "failed")).sum()
    )
    features["failed_retry_rate"] = safe_division(features["failed_retry_count"], n)

    # --- 5. Device and IP concentration ---
    dev_unique, dev_diversity, dev_top_share, dev_entropy = compute_concentration_metrics(
        window_txns["device_id"]
    )
    features["unique_device_count"] = dev_unique
    features["device_diversity_ratio"] = dev_diversity
    features["top_device_share"] = dev_top_share
    features["device_entropy"] = dev_entropy

    ip_unique, ip_diversity, ip_top_share, ip_entropy = compute_concentration_metrics(
        window_txns["ip_id"]
    )
    features["unique_ip_count"] = ip_unique
    features["ip_diversity_ratio"] = ip_diversity
    features["top_ip_share"] = ip_top_share
    features["ip_entropy"] = ip_entropy

    # --- 6. Customer behavior ---
    cust_unique, cust_diversity, _, _ = compute_concentration_metrics(
        window_txns["customer_id"]
    )
    features["unique_customer_count"] = cust_unique
    features["customer_diversity_ratio"] = cust_diversity

    new_count = int(window_txns["customer_is_new"].sum())
    repeat_count = n - new_count
    features["new_customer_share"] = safe_division(new_count, n)
    features["repeat_customer_share"] = safe_division(repeat_count, n)

    return features


# ---------------------------------------------------------------------------
# Historical baseline features
# ---------------------------------------------------------------------------


def compute_historical_features(
    merchant_window_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute merchant-relative historical baseline features using only prior dates.

    The current day's transaction count is NOT included in its own baseline.

    Args:
        merchant_window_df: DataFrame for a single merchant, sorted by date.
            Must include 'date' and 'transaction_count' columns.

    Returns:
        DataFrame with historical features added.
    """
    df = merchant_window_df.sort_values("date").copy()
    n = len(df)

    rolling_mean = np.zeros(n)
    rolling_std = np.zeros(n)
    zscore = np.zeros(n)
    ratio_to_mean = np.zeros(n)

    for i in range(n):
        # Use only observations BEFORE the current day
        start_idx = max(0, i - 7)  # lookback of up to 7 previous days
        prior_counts = df["transaction_count"].values[start_idx:i]

        if len(prior_counts) == 0:
            # No historical data: use safe defaults
            rolling_mean[i] = df["transaction_count"].values[i]
            rolling_std[i] = 0.0
            zscore[i] = 0.0
            ratio_to_mean[i] = 1.0
            continue

        mean_val = np.mean(prior_counts)
        std_val = np.std(prior_counts, ddof=1) if len(prior_counts) > 1 else 0.0

        rolling_mean[i] = mean_val
        rolling_std[i] = std_val

        # Z-score: how many standard deviations is current day from historical mean
        if std_val > 0:
            zscore[i] = (df["transaction_count"].values[i] - mean_val) / std_val
        else:
            zscore[i] = 0.0

        # Ratio to historical mean
        if mean_val > 0:
            ratio_to_mean[i] = df["transaction_count"].values[i] / mean_val
        else:
            ratio_to_mean[i] = 1.0

    df["volume_rolling_mean_7d"] = rolling_mean
    df["volume_rolling_std_7d"] = rolling_std
    df["volume_zscore_7d"] = zscore
    df["volume_ratio_to_7d_mean"] = ratio_to_mean

    return df


# ---------------------------------------------------------------------------
# Feature column list
# ---------------------------------------------------------------------------


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Return model feature columns, excluding metadata and target.

    Args:
        df: DataFrame containing all columns.

    Returns:
        List of column names suitable for model training.
    """
    exclude = set(METADATA_COLUMNS)
    return [col for col in df.columns if col not in exclude]


# ---------------------------------------------------------------------------
# Main aggregation pipeline
# ---------------------------------------------------------------------------


def build_window_features(
    transactions: pd.DataFrame,
    window_labels: pd.DataFrame,
) -> pd.DataFrame:
    """
    Aggregate transaction-level data into one feature row per merchant-day.

    Args:
        transactions: Raw transaction-level data.
        window_labels: Window-level labels with merchant_id, date, window_label.

    Returns:
        DataFrame with one row per merchant-date and all engineered features.
    """
    # Validate input columns
    missing = set(REQUIRED_TXN_COLUMNS) - set(transactions.columns)
    if missing:
        raise ValueError(f"Missing required columns in transactions: {missing}")

    # Convert date columns to consistent type for grouping
    txn = transactions.copy()
    txn["date"] = pd.to_datetime(txn["date"])
    labels = window_labels.copy()
    labels["date"] = pd.to_datetime(labels["date"])

    # Group transactions by merchant-day
    grouped = txn.groupby(["merchant_id", "date"])

    # Compute behavioral features for each window
    feature_rows = []
    for (merchant_id, date), window_txns in grouped:
        features = compute_window_features(window_txns)
        features["merchant_id"] = merchant_id
        features["date"] = date
        feature_rows.append(features)

    features_df = pd.DataFrame(feature_rows)

    # Merge with window labels
    features_df = features_df.merge(
        labels[["merchant_id", "date", "window_label", "transaction_count"]],
        on=["merchant_id", "date"],
        how="left",
        suffixes=("_behavioral", "_label"),
    )

    # Use the label's transaction_count as authoritative
    if "transaction_count_behavioral" in features_df.columns:
        features_df = features_df.drop(columns=["transaction_count_behavioral"])
    if "transaction_count_label" in features_df.columns:
        features_df = features_df.rename(columns={"transaction_count_label": "transaction_count"})

    # Compute historical baseline features per merchant
    merchant_dfs = []
    for merchant_id, group in features_df.groupby("merchant_id"):
        merchant_dfs.append(compute_historical_features(group))

    result = pd.concat(merchant_dfs, ignore_index=True)

    # Ensure window_label is present
    if "window_label" not in result.columns:
        raise ValueError("window_label missing after merge")

    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_features(
    features_df: pd.DataFrame,
    expected_merchants: int = 8,
    expected_days: int = 45,
) -> list[str]:
    """Validate the feature DataFrame.

    Returns a list of error messages (empty = valid).
    """
    errors: list[str] = []

    # 1. Required columns exist
    for col in ["merchant_id", "date", "window_label", "transaction_count"]:
        if col not in features_df.columns:
            errors.append(f"Missing required column: {col}")

    # 2. Correct window count
    expected_windows = expected_merchants * expected_days
    actual_windows = len(features_df)
    if actual_windows != expected_windows:
        errors.append(f"Expected {expected_windows} windows, got {actual_windows}")

    # 3. No duplicate merchant-date pairs
    duplicates = features_df.duplicated(subset=["merchant_id", "date"])
    if duplicates.any():
        errors.append(f"{duplicates.sum()} duplicate merchant-date pairs")

    # 4. No missing values
    missing_counts = features_df.isnull().sum()
    cols_with_missing = missing_counts[missing_counts > 0]
    if len(cols_with_missing) > 0:
        errors.append(f"Columns with missing values: {dict(cols_with_missing)}")

    # 5. No infinite values
    numeric_cols = features_df.select_dtypes(include=[np.number]).columns
    inf_counts = np.isinf(features_df[numeric_cols]).sum()
    cols_with_inf = inf_counts[inf_counts > 0]
    if len(cols_with_inf) > 0:
        errors.append(f"Columns with infinite values: {dict(cols_with_inf)}")

    # 6. Rate/share features are between 0 and 1
    rate_cols = [
        "success_rate",
        "failed_payment_rate",
        "retry_rate",
        "failed_retry_rate",
        "sku_diversity_ratio",
        "top_sku_share",
        "device_diversity_ratio",
        "top_device_share",
        "ip_diversity_ratio",
        "top_ip_share",
        "customer_diversity_ratio",
        "new_customer_share",
        "repeat_customer_share",
    ]
    for col in rate_cols:
        if col in features_df.columns:
            vals = features_df[col]
            if (vals < -0.01).any() or (vals > 1.01).any():
                errors.append(f"{col} has values outside [0, 1]: min={vals.min():.4f}, max={vals.max():.4f}")

    # 7. success_rate + failed_payment_rate approximately 1
    if "success_rate" in features_df.columns and "failed_payment_rate" in features_df.columns:
        total_rate = features_df["success_rate"] + features_df["failed_payment_rate"]
        if not np.allclose(total_rate, 1.0, atol=0.01):
            errors.append(f"success_rate + failed_payment_rate not approximately 1: mean={total_rate.mean():.4f}")

    # 8. new_customer_share + repeat_customer_share approximately 1
    if "new_customer_share" in features_df.columns and "repeat_customer_share" in features_df.columns:
        total_share = features_df["new_customer_share"] + features_df["repeat_customer_share"]
        if not np.allclose(total_share, 1.0, atol=0.01):
            errors.append(f"new_customer_share + repeat_customer_share not approximately 1: mean={total_share.mean():.4f}")

    # 9. Entropy values are non-negative
    entropy_cols = ["sku_entropy", "device_entropy", "ip_entropy"]
    for col in entropy_cols:
        if col in features_df.columns:
            if (features_df[col] < -0.01).any():
                errors.append(f"{col} has negative values")

    # 10. Standard deviation values are non-negative
    std_cols = ["amount_std", "volume_rolling_std_7d"]
    for col in std_cols:
        if col in features_df.columns:
            if (features_df[col] < -0.01).any():
                errors.append(f"{col} has negative values")

    return errors


# ---------------------------------------------------------------------------
# Save and run
# ---------------------------------------------------------------------------


def save_features(
    features_df: pd.DataFrame,
    output_path: str = "data/processed/window_features.csv",
) -> str:
    """Save feature DataFrame to CSV."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    features_df.to_csv(output_path, index=False)
    return output_path


def main(
    input_path: str = "data/raw/transactions.csv",
    output_path: str = "data/processed/window_features.csv",
) -> None:
    """Main entry point: load data, engineer features, validate, and save."""
    print("=" * 60)
    print("SUS - Window-Level Feature Engineering")
    print("=" * 60)

    # Load data
    print("\n[1/4] Loading data...")
    transactions = pd.read_csv(input_path)
    labels_path = input_path.replace("transactions.csv", "window_labels.csv")
    window_labels = pd.read_csv(labels_path)
    print(f"  Input transactions: {len(transactions):,}")

    # Build features
    print("\n[2/4] Computing window-level features...")
    features_df = build_window_features(transactions, window_labels)
    print(f"  Output windows: {len(features_df)}")
    print(f"  Feature count: {len(get_feature_columns(features_df))}")

    # Validate
    print("\n[3/4] Validating features...")
    errors = validate_features(features_df)
    if errors:
        print("  ERRORS found:")
        for e in errors:
            print(f"    ✗ {e}")
        raise ValueError("Feature validation failed. See errors above.")
    print("  All validation checks passed")

    # Save
    print("\n[4/4] Saving features...")
    saved_path = save_features(features_df, output_path)
    print(f"  Output: {saved_path}")

    # Summary
    print("\n" + "=" * 60)
    print("Feature Summary")
    print("=" * 60)
    print(f"  Total input transactions:  {len(transactions):,}")
    print(f"  Output windows:            {len(features_df)}")
    print(f"  Number of features:        {len(get_feature_columns(features_df))}")
    print(f"  Column list:               {list(features_df.columns)}")

    # Check for NaN/inf
    nan_count = features_df.isnull().sum().sum()
    inf_count = np.isinf(features_df.select_dtypes(include=[np.number])).sum().sum()
    print(f"  NaN values:                {nan_count}")
    print(f"  Infinite values:           {inf_count}")

    # Class distribution
    if "window_label" in features_df.columns:
        label_dist = features_df["window_label"].value_counts()
        print(f"\n  Class distribution:")
        for label, count in label_dist.items():
            print(f"    {label:20s} {count:>5d} ({count / len(features_df) * 100:.1f}%)")

    print("\nDone!")


if __name__ == "__main__":
    main()
